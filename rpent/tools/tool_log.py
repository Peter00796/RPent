"""Append-only record of every tool call in a run.

``states.json`` only gains an entry when a primitive advances the environment, so
the read-only half of a run — every ``segment``, ``back_project``,
``world_extent``, ``compare_extent`` and every file the agent read — left no trace
in the run's evidence at all. It appeared only in the planner's transcript, which
is a planner-layer artifact: a different backend produces a different shape, and
a diagnostic script cannot rely on it.

That gap blocks attribution. "Which reading did this motion come from" and "what
evidence had the agent gathered before it committed" are the questions any
post-hoc analysis starts with, and neither is answerable from ``states.json``
alone.

Records live in ``tool_calls.jsonl`` beside ``states.json`` because both are raw
records of what happened, not derived analysis. ``step_idx`` is captured before
and after each call, so whether a call advanced the environment is computed from
the log rather than declared in it — and a read-only call is pinned to the env
state it observed.

This module imports nothing beyond the standard library, so diagnostics and
offline analysis can read a run without pulling in the agent framework.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

FILENAME = "tool_calls.jsonl"

#: Cap on one record's serialised result, in characters. Results are normally a
#: few KB; this only stops a pathological one from dominating the file.
MAX_RESULT_CHARS = 32000

#: A turn's tool calls run concurrently in this process, so appends race and the
#: sequence number would not be monotonic without a lock. The writers are threads
#: in one process, so a module lock is the whole fix.
_LOCK = threading.Lock()
_SEQ = 0


def path_for(output_dir: str | os.PathLike[str]) -> Path:
    return Path(output_dir) / FILENAME


def reset_sequence() -> None:
    """Restart numbering. Call once per run, before the first append."""
    global _SEQ
    with _LOCK:
        _SEQ = 0


def append(
    output_dir: str | os.PathLike[str],
    *,
    tool: str,
    args: dict[str, Any] | None,
    result: Any,
    elapsed_s: float,
    step_idx_before: int | None = None,
    step_idx_after: int | None = None,
    status: str = "success",
    call_id: str | None = None,
) -> None:
    """Append one tool call. Never raises — recording must not break a run.

    ``call_id`` is the provider's tool-call id when the caller has one. It is
    what lets a message-list ToolMessage be joined back to its record exactly
    (the resident session's folding digests depend on that join); older logs
    without the field still load fine.
    """
    global _SEQ
    try:
        rendered = _render_result(result)
        with _LOCK:
            _SEQ += 1
            record = {
                "schema_version": SCHEMA_VERSION,
                "seq": _SEQ,
                "tool": tool,
                "args": args or {},
                "status": status,
                "elapsed_s": round(float(elapsed_s), 3),
                "step_idx_before": step_idx_before,
                "step_idx_after": step_idx_after,
                "result": rendered,
            }
            if call_id:
                record["call_id"] = call_id
            target = path_for(output_dir)
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "a") as handle:
                handle.write(json.dumps(record, default=str) + "\n")
    except Exception:
        # A missing log line is a smaller loss than a failed episode.
        return


def load(output_dir: str | os.PathLike[str]) -> list[dict[str, Any]]:
    """Return every recorded call, in order. Malformed lines are skipped."""
    target = path_for(output_dir)
    if not target.exists():
        return []
    records: list[dict[str, Any]] = []
    with open(target) as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                continue
    return records


def _render_result(result: Any) -> Any:
    """Keep the result structured where possible, bounded in size always.

    ``entity_index`` is dropped: it is a snapshot of ``analysis/entities.json``,
    which is already stored with its full history, so copying it into every
    record would bloat the log without adding anything recoverable.
    """
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except Exception:
            return result[:MAX_RESULT_CHARS]
    if isinstance(result, dict):
        result = {k: v for k, v in result.items() if k != "entity_index"}
    try:
        serialised = json.dumps(result, default=str)
    except Exception:
        return str(result)[:MAX_RESULT_CHARS]
    if len(serialised) <= MAX_RESULT_CHARS:
        return result
    return {
        "_truncated": True,
        "_chars": len(serialised),
        "_head": serialised[:MAX_RESULT_CHARS],
    }
