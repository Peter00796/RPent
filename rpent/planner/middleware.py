"""Middleware for the LangChain planner — one unit per cross-cutting concern.

Before this layer existed, transcript serialisation, usage accounting and
dashboard projection were inlined in the agent loop *and* reimplemented in each
CLI-agent planner. They are not tool logic and not loop logic; they are
cross-cutting, so each one belongs in exactly one middleware with a declared
position in the chain.

:data:`MIDDLEWARE_ORDER` is that declaration. It is part of the run's identity —
a different order is a different method — so it is recorded, not implicit.

:class:`TranscriptMiddleware` and :class:`ToolCallLogMiddleware` are implemented.
The remaining entries are named on purpose: they are the concerns known to be
missing, and naming them here is cheaper than rediscovering them later. Where
LangChain already ships a prebuilt middleware for one, it is noted so we adopt
rather than reinvent.

Hooks available on ``AgentMiddleware`` (langchain 1.3):

- ``before_agent`` / ``after_agent``  — episode lifecycle
- ``before_model`` / ``after_model``  — per-turn state
- ``wrap_model_call(request, handler)`` — ``request`` carries ``messages``,
  ``system_message`` and ``tools``, i.e. exactly what reaches the provider. This
  is the anchor for injection accounting.
- ``wrap_tool_call(request, handler)`` — ``request`` carries ``tool_call``,
  ``tool``, ``state`` and ``runtime``. This is the anchor for gates.
"""

import json
import time
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage, ToolMessage

from rpent.dashboard.events import (
    DashboardEventSink,
    TranscriptEvent,
    UsageEvent,
)
from rpent.tools import tool_log
from rpent.utils.logging import get_logger

logger = get_logger("planner_middleware")

#: Console-log truncation limits (characters), matching the pydantic-ai planner.
_TEXT_LOG_LIMIT = 500
_ARGS_LOG_LIMIT = 250
_TOOL_LOG_LIMIT = 350

#: Declared middleware order, outermost first. Entries marked "not implemented"
#: are known gaps, not oversights.
MIDDLEWARE_ORDER: tuple[tuple[str, str], ...] = (
    ("ModelCallLimitMiddleware", "turn budget (prebuilt: langchain)"),
    ("TranscriptMiddleware", "transcript + usage + dashboard projection"),
    ("ToolCallLogMiddleware", "run-evidence record of every tool call"),
    ("AttemptFoldingMiddleware",
     "resident sessions only: archived attempts' tool results fold into "
     "seq-cited one-line digests (the first legitimate compaction — the "
     "folded prefix is byte-stable, so it stays cache-friendly)"),
    ("ToolCallIntegrityMiddleware",
     "innermost: repair orphan tool_calls pre-flight; dump the outbound "
     "request on provider rejection (gen-0 t5 400 incident)"),
    ("InjectionLedgerMiddleware", "not implemented — per-component token accounting"),
    ("GateMiddleware", "not implemented — hard gates + shadow mode on advancing tools"),
    ("ProvenanceMiddleware", "not implemented — argument-level evidence provenance"),
    (
        "CompactionMiddleware",
        "not implemented for exam runs — env-unsafe, and cache-hostile: "
        "rewriting the middle of the message list invalidates every automatic "
        "prefix cache from that point on, so its token saving is partly "
        "offset. Prebuilt: Summarization, ContextEditing",
    ),
)


class TranscriptMiddleware(AgentMiddleware):
    """Record the run: transcript, token usage, tool calls, finish signal.

    Owns every observation of the loop that is not the loop itself. The planner
    reads the accumulated state off this object after the run instead of
    threading recording through the agent graph.
    """

    def __init__(
        self,
        *,
        dashboard_events: DashboardEventSink,
        max_turns: int,
    ) -> None:
        super().__init__()
        self._dashboard_events = dashboard_events
        self._max_turns = max_turns
        #: Serialisable transcript, shaped like the other planners' output so
        #: ``PlannerResult.messages`` stays comparable across backends.
        self.messages: list[dict[str, Any]] = []
        self.turns = 0
        self.tool_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_read_tokens = 0
        self.cache_write_tokens = 0
        self.requests = 0
        self.finish_result: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Model turns
    # ------------------------------------------------------------------

    def after_model(self, state: Any, runtime: Any) -> None:
        """Record the assistant turn the model just produced."""
        messages = state.get("messages") or []
        if not messages:
            return
        message = messages[-1]
        if not isinstance(message, AIMessage):
            return

        self.turns += 1
        self.requests += 1
        self._add_usage(message)

        serialized = _serialize_ai_message(message)
        self.messages.append(serialized)
        _log_turn(serialized, self.turns, self._max_turns, self._usage_summary())

        for block in serialized["content"]:
            if block["type"] == "text":
                payload = {"type": "text", "text": block["text"]}
            elif block["type"] == "thinking":
                payload = {"type": "thinking", "text": block["thinking"]}
            else:
                continue
            self._dashboard_events.emit(TranscriptEvent(payload))
        self._emit_usage()
        return None

    # ------------------------------------------------------------------
    # Tool calls
    # ------------------------------------------------------------------

    def wrap_tool_call(self, request: Any, handler: Any) -> Any:
        """Record one tool call and its result, then delegate to the handler."""
        call = request.tool_call
        name = call.get("name", "")
        args = call.get("args") or {}
        self.tool_calls += 1
        self._dashboard_events.emit(
            TranscriptEvent({"type": "tool_call", "tool": name, "args": args})
        )
        # ``finish`` is the env-provided halt signal; capture its arguments as
        # the run outcome exactly as the other planners do. The tool still runs.
        if name == "finish":
            self.finish_result = {"_finish": True, **args}

        result = handler(request)

        if isinstance(result, ToolMessage):
            content = result.content
            text = content if isinstance(content, str) else _content_text(content)
            self.messages.append(
                {
                    "role": "tool",
                    "name": result.name or name,
                    "tool_call_id": result.tool_call_id,
                    "content": text,
                }
            )
            logger.info("[tool<] %s: %s", name, _clip(" ".join(text.split()), _TOOL_LOG_LIMIT))
            self._dashboard_events.emit(
                TranscriptEvent(
                    {
                        "type": "tool_result",
                        "tool": result.name or name,
                        "result": {
                            "is_error": result.status == "error",
                            "size": len(text),
                        },
                    }
                )
            )
        self._emit_usage()
        return result

    # ------------------------------------------------------------------
    # Accounting
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Return the run stats in the shape every planner reports."""
        return {
            "turns_used": self.turns,
            "tool_calls": self.tool_calls,
            "total_input_tokens": self.input_tokens,
            "total_output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "requests": self.requests,
        }

    def _add_usage(self, message: AIMessage) -> None:
        usage = message.usage_metadata or {}
        self.input_tokens += int(usage.get("input_tokens") or 0)
        self.output_tokens += int(usage.get("output_tokens") or 0)
        details = usage.get("input_token_details") or {}
        read = int(details.get("cache_read") or 0)
        written = int(details.get("cache_creation") or 0)
        if not read and not written:
            read, written = _provider_cache_tokens(message)
        self.cache_read_tokens += read
        self.cache_write_tokens += written

    def _usage_summary(self) -> str:
        return (
            f"in={self.input_tokens} out={self.output_tokens} "
            f"cache_read={self.cache_read_tokens} "
            f"cache_write={self.cache_write_tokens} requests={self.requests}"
        )

    def _emit_usage(self) -> None:
        self._dashboard_events.emit(
            UsageEvent(
                inp=self.input_tokens,
                out=self.output_tokens,
                tool_calls=self.tool_calls,
            )
        )


class ToolCallLogMiddleware(AgentMiddleware):
    """Record every tool call into the run's evidence, not just the transcript.

    Separate from :class:`TranscriptMiddleware` on purpose: that one feeds the
    planner's own output and the dashboard, this one writes a run artifact whose
    consumers are diagnostics and any later reflection pass. They have different
    audiences and different retention, so they are different concerns — and this
    one has to be independently toggleable, because it is the input to any
    attribution done after the fact.

    Environment-agnostic: the step index is read off the run context only if that
    context happens to expose one, so nothing here knows what a LIBERO step is.
    """

    def __init__(self, *, output_dir: Any) -> None:
        super().__init__()
        self._output_dir = output_dir
        tool_log.reset_sequence()

    def wrap_tool_call(self, request: Any, handler: Any) -> Any:
        call = request.tool_call
        name = call.get("name", "")
        args = call.get("args") or {}
        call_id = call.get("id")
        before = self._step_index(request)
        started = time.monotonic()
        try:
            result = handler(request)
        except Exception as exc:
            tool_log.append(
                self._output_dir,
                tool=name,
                args=args,
                result={"exception": f"{type(exc).__name__}: {exc}"},
                elapsed_s=time.monotonic() - started,
                step_idx_before=before,
                step_idx_after=self._step_index(request),
                status="raised",
                call_id=call_id,
            )
            raise
        content = getattr(result, "content", result)
        tool_log.append(
            self._output_dir,
            tool=name,
            args=args,
            result=content,
            elapsed_s=time.monotonic() - started,
            step_idx_before=before,
            step_idx_after=self._step_index(request),
            status=getattr(result, "status", "success") or "success",
            call_id=call_id,
        )
        return result

    @staticmethod
    def _step_index(request: Any) -> int | None:
        context = getattr(getattr(request, "runtime", None), "context", None)
        value = getattr(context, "step_idx", None)
        return int(value) if isinstance(value, int) else None


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


#: Provider-native cache field names to fall back on, as
#: ``(read_field, written_field)`` pairs searched in ``response_metadata``.
#: LangChain normalises OpenAI's ``cached_tokens`` and Anthropic's cache fields
#: into ``usage_metadata.input_token_details``, but a provider that reports cache
#: usage under its own names is normalised to nothing — and silently reading
#: zero cache hits is worse than reading none, because the ledger then claims the
#: cache never worked. DeepSeek is the case in point: its context cache is
#: automatic server-side prefix caching (there is nothing to enable client-side),
#: and it reports the outcome as ``prompt_cache_hit_tokens`` /
#: ``prompt_cache_miss_tokens``, which no adapter maps today.
_PROVIDER_CACHE_FIELDS: tuple[tuple[str, str | None], ...] = (
    ("prompt_cache_hit_tokens", None),  # DeepSeek
    ("cached_tokens", None),  # OpenAI-compatible, if left unmapped
)


def _provider_cache_tokens(message: AIMessage) -> tuple[int, int]:
    """Recover cache token counts from provider-native usage fields.

    Returns ``(read, written)``. Providers with automatic prefix caching report
    only hits, so ``written`` stays 0 for them — there is no client-controlled
    cache write to attribute.
    """
    meta = message.response_metadata or {}
    candidates: list[dict[str, Any]] = [meta]
    for key in ("token_usage", "usage", "prompt_tokens_details"):
        value = meta.get(key)
        if isinstance(value, dict):
            candidates.append(value)
            nested = value.get("prompt_tokens_details")
            if isinstance(nested, dict):
                candidates.append(nested)
    for read_field, write_field in _PROVIDER_CACHE_FIELDS:
        for blob in candidates:
            if read_field in blob:
                written = int(blob.get(write_field) or 0) if write_field else 0
                return int(blob.get(read_field) or 0), written
    return 0, 0


def _serialize_ai_message(message: AIMessage) -> dict[str, Any]:
    """Render one assistant turn as a serialisable transcript message."""
    content: list[dict[str, Any]] = []
    raw = message.content
    if isinstance(raw, str):
        if raw:
            content.append({"type": "text", "text": raw})
    elif isinstance(raw, list):
        for block in raw:
            if isinstance(block, str):
                if block:
                    content.append({"type": "text", "text": block})
            elif isinstance(block, dict):
                kind = block.get("type")
                if kind == "text" and block.get("text"):
                    content.append({"type": "text", "text": block["text"]})
                elif kind == "thinking" and block.get("thinking"):
                    content.append({"type": "thinking", "thinking": block["thinking"]})
    for call in message.tool_calls or ():
        content.append(
            {
                "type": "tool_use",
                "id": call.get("id"),
                "name": call.get("name"),
                "input": call.get("args") or {},
            }
        )
    return {"role": "assistant", "content": content}


def _content_text(content: Any) -> str:
    """Flatten block-list tool content into text, dropping image payloads."""
    if not isinstance(content, list):
        return str(content)
    parts = [
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    return "\n\n".join(p for p in parts if p)


def _log_turn(
    serialized: dict[str, Any], turn: int, max_turns: int, usage: str
) -> None:
    """Log model text, thinking, and tool calls for one turn."""
    import json

    logger.info("=== turn %d/%d ===", turn, max_turns)
    for block in serialized["content"]:
        if block["type"] == "text":
            logger.info("[model] %s", _clip(block["text"].strip(), _TEXT_LOG_LIMIT))
        elif block["type"] == "thinking":
            logger.info("[think] %s", _clip(block["thinking"].strip(), _TEXT_LOG_LIMIT))
        elif block["type"] == "tool_use":
            args = json.dumps(block["input"], default=str)
            logger.info("[tool>] %s(%s)", block["name"], _clip(args, _ARGS_LOG_LIMIT))
    logger.info("[usage] %s", usage)


def _clip(text: str, limit: int) -> str:
    """Truncate ``text`` to ``limit`` characters with an overflow marker."""
    if len(text) <= limit:
        return text
    return text[:limit] + "...(+%d)" % (len(text) - limit)


class ToolCallIntegrityMiddleware(AgentMiddleware):
    """Repair the one provider-fatal state invariant before each model call.

    Field incident (gen-0 t5, 2026-08-07): DeepSeek rejected the 8th request
    with 400 ``insufficient tool messages following tool_calls`` after a
    16-parallel-call turn, killing the run — while the transcript held a
    perfectly paired 50/50 record. The corruption was in the outbound message
    list, which nothing dumped, so the root cause is still open. Two
    mechanisms follow, both valid whatever that root cause turns out to be:

    - **Pre-flight repair**: before the request leaves, every assistant
      ``tool_call`` id must be answered by a ``ToolMessage``. An orphan gets a
      synthesized error ToolMessage (telling the model the result was lost and
      to re-issue the call), an ERROR log line, and a record in
      ``analysis/anomalies.jsonl`` — a run-killing 400 becomes a recorded,
      recoverable anomaly.
    - **Crime-scene dump**: if the provider still rejects the request, the
      exact outbound message list is written to
      ``analysis/request_failure.json`` before the exception propagates, so
      the next occurrence is a full diagnosis, not a guess.

    Innermost in the chain on purpose: it must see the final request, after
    every other middleware has had its say.
    """

    def __init__(self, *, output_dir: Any) -> None:
        super().__init__()
        self._output_dir = output_dir

    # -- helpers ---------------------------------------------------------

    def _analysis_dir(self):
        from pathlib import Path

        path = Path(self._output_dir) / "analysis"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _record_anomaly(self, record: dict) -> None:
        import json

        with open(self._analysis_dir() / "anomalies.jsonl", "a") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def _repair(self, messages: list) -> tuple[list, int]:
        answered = {
            m.tool_call_id for m in messages if isinstance(m, ToolMessage)
        }
        repaired: list = []
        synthesized = 0
        for message in messages:
            repaired.append(message)
            if not isinstance(message, AIMessage) or not message.tool_calls:
                continue
            for call in message.tool_calls:
                call_id = call.get("id")
                if not call_id or call_id in answered:
                    continue
                synthesized += 1
                answered.add(call_id)
                logger.error(
                    "orphan tool_call %s (%s): no ToolMessage in state — "
                    "synthesizing an error result so the request stays valid",
                    call_id, call.get("name"),
                )
                self._record_anomaly({
                    "kind": "orphan_tool_call",
                    "tool_call_id": call_id,
                    "tool": call.get("name"),
                    "time": time.time(),
                })
                repaired.append(ToolMessage(
                    content='{"error": "this tool result was lost by the '
                            'framework; treat the call as failed and re-issue '
                            'it if still needed"}',
                    tool_call_id=call_id,
                    name=call.get("name") or "unknown",
                ))
        return repaired, synthesized

    def _dump_failure(self, messages: list, error: Exception) -> None:
        import json

        payload = {
            "error": f"{type(error).__name__}: {error}",
            "time": time.time(),
            "messages": [
                {
                    "type": type(m).__name__,
                    "tool_call_id": getattr(m, "tool_call_id", None),
                    "tool_calls": [
                        {"id": c.get("id"), "name": c.get("name")}
                        for c in (getattr(m, "tool_calls", None) or ())
                    ],
                    "content": str(getattr(m, "content", ""))[:2000],
                }
                for m in messages
            ],
        }
        target = self._analysis_dir() / "request_failure.json"
        target.write_text(json.dumps(payload, indent=2, default=str))
        logger.error("provider rejected the request; outbound state dumped to %s",
                     target)

    # -- hook --------------------------------------------------------------

    def wrap_model_call(self, request: Any, handler: Any) -> Any:
        messages = list(getattr(request, "messages", None) or ())
        repaired, synthesized = self._repair(messages)
        if synthesized:
            if hasattr(request, "override"):
                request = request.override(messages=repaired)
            else:
                request.messages = repaired
        try:
            return handler(request)
        except Exception as exc:
            if "tool" in str(exc).lower() or "400" in str(exc):
                self._dump_failure(repaired, exc)
            raise


class AttemptFoldingMiddleware(AgentMiddleware):
    """Fold archived attempts' tool results into one-line digests.

    Resident debug sessions only. The wall this removes: a session that
    remembers three failed attempts verbatim exhausts a flash-sized context;
    a session that forgets them entirely is the amnesiac loop again. The
    ASPIRE-shaped middle: the model keeps its own REASONING from every
    attempt, each archived tool result shrinks to one line carrying its
    citation key ``[attempt N seq M]``, and the full record stays on disk,
    retrievable one call at a time via ``view_attempt_call``.

    Folding is a per-REQUEST view built in ``wrap_model_call`` — the graph
    state and the transcript keep the original messages, so the disk record
    stays complete. Attempt boundaries are the ``reset_episode`` ToolMessages
    in the message list; everything before the last one belongs to an
    archived attempt. The join from a ToolMessage to its logged record is by
    ``call_id`` (exact), written by :class:`ToolCallLogMiddleware`.

    Cache note: a folded prefix is byte-stable across turns (archives are
    immutable), so unlike mid-list summarisation this compaction keeps the
    provider's automatic prefix cache warm after the first post-reset turn.
    """

    #: Head of the archived result kept in the digest, chars.
    _BRIEF_CHARS = 110

    def __init__(self, *, output_dir: Any) -> None:
        super().__init__()
        from pathlib import Path

        self._output_dir = Path(output_dir)
        #: attempt number -> {call_id: record}. Archives are immutable, so
        #: a loaded map never invalidates.
        self._seq_maps: dict[int, dict[str, dict]] = {}

    def _seq_map(self, attempt: int) -> dict[str, dict]:
        if attempt not in self._seq_maps:
            records = tool_log.load(
                self._output_dir / f"attempt_{attempt:02d}")
            self._seq_maps[attempt] = {
                r["call_id"]: r for r in records if r.get("call_id")
            }
        return self._seq_maps[attempt]

    def _digest(self, message: ToolMessage, attempt: int) -> ToolMessage:
        record = self._seq_map(attempt).get(message.tool_call_id or "")
        name = message.name or (record or {}).get("tool") or "tool"
        if record is None:
            text = (f"[attempt {attempt}] {name}: result archived; no "
                    f"per-call record found — raw log: "
                    f"attempt_{attempt:02d}/tool_calls.jsonl")
        else:
            result = record.get("result")
            if isinstance(result, dict) and result.get("error"):
                brief = f"error: {str(result['error'])}"
            else:
                brief = json.dumps(result, default=str) if not isinstance(
                    result, str) else result
            brief = " ".join(brief.split())
            if len(brief) > self._BRIEF_CHARS:
                brief = brief[:self._BRIEF_CHARS] + "…"
            text = (f"[attempt {attempt} seq {record['seq']}] {name} -> "
                    f"{record.get('status', '?')}; {brief} | full record: "
                    f"view_attempt_call(attempt={attempt}, "
                    f"seq={record['seq']})")
        return ToolMessage(
            content=text,
            tool_call_id=message.tool_call_id,
            name=message.name,
            status=getattr(message, "status", None) or "success",
        )

    def _fold(self, messages: list) -> tuple[list, int]:
        n_resets = sum(
            1 for m in messages
            if isinstance(m, ToolMessage) and m.name == "reset_episode"
        )
        if n_resets == 0:
            return messages, 0
        folded: list = []
        seen_resets = 0
        n_folded = 0
        for message in messages:
            if isinstance(message, ToolMessage):
                if message.name == "reset_episode":
                    # The boundary marker itself stays readable: it carries
                    # the fresh step-0 view the next attempt started from.
                    seen_resets += 1
                elif seen_resets < n_resets:
                    folded.append(self._digest(message, seen_resets + 1))
                    n_folded += 1
                    continue
            folded.append(message)
        return folded, n_folded

    def wrap_model_call(self, request: Any, handler: Any) -> Any:
        messages = list(getattr(request, "messages", None) or ())
        folded, n_folded = self._fold(messages)
        if n_folded:
            if hasattr(request, "override"):
                request = request.override(messages=folded)
            else:
                request.messages = folded
        return handler(request)
