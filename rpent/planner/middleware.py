"""Middleware for the LangChain planner — one unit per cross-cutting concern.

Before this layer existed, transcript serialisation, usage accounting and
dashboard projection were inlined in the agent loop *and* reimplemented in each
CLI-agent planner. They are not tool logic and not loop logic; they are
cross-cutting, so each one belongs in exactly one middleware with a declared
position in the chain.

:data:`MIDDLEWARE_ORDER` is that declaration. It is part of the run's identity —
a different order is a different method — so it is recorded, not implicit.

Only :class:`TranscriptMiddleware` is implemented. The remaining entries are
named on purpose: they are the concerns known to be missing, and naming them
here is cheaper than rediscovering them later. Where LangChain already ships a
prebuilt middleware for one, it is noted so we adopt rather than reinvent.

Hooks available on ``AgentMiddleware`` (langchain 1.3):

- ``before_agent`` / ``after_agent``  — episode lifecycle
- ``before_model`` / ``after_model``  — per-turn state
- ``wrap_model_call(request, handler)`` — ``request`` carries ``messages``,
  ``system_message`` and ``tools``, i.e. exactly what reaches the provider. This
  is the anchor for injection accounting.
- ``wrap_tool_call(request, handler)`` — ``request`` carries ``tool_call``,
  ``tool``, ``state`` and ``runtime``. This is the anchor for gates.
"""

from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage, ToolMessage

from rpent.dashboard.events import (
    DashboardEventSink,
    TranscriptEvent,
    UsageEvent,
)
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
    ("InjectionLedgerMiddleware", "not implemented — per-component token accounting"),
    ("GateMiddleware", "not implemented — hard gates + shadow mode on advancing tools"),
    ("ProvenanceMiddleware", "not implemented — argument-level evidence provenance"),
    (
        "CompactionMiddleware",
        "not implemented — env-unsafe, and cache-hostile: rewriting the middle of "
        "the message list invalidates every automatic prefix cache from that "
        "point on, so its token saving is partly offset. Prebuilt: Summarization, "
        "ContextEditing",
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
