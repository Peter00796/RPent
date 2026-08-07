"""Join a run's logs into one evidence timeline.

``tool_calls.jsonl`` is the ground truth (every call, seq-ordered, with the
result the model saw); the transcript contributes the reasoning text each
assistant turn emitted before its calls. The join is positional with a name
check — both files are written by the same single-threaded loop, so order is
identity, and any mismatch is reported as a warning rather than papered over.

Stdlib only, like :mod:`rpent.tools.tool_log`: diagnostics must be able to
read a run without the agent framework installed.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from rpent.tools import tool_log


@dataclass
class Call:
    """One tool call, with the reasoning that preceded it."""

    seq: int
    tool: str
    args: dict
    status: str
    elapsed_s: float | None
    step_before: int | None
    step_after: int | None
    result: object
    reasoning: str = ""
    turn: int = 0

    @property
    def advanced(self) -> bool:
        """Computed from the log, not declared (the tool_calls.jsonl contract)."""
        return (
            self.step_before is not None
            and self.step_after is not None
            and self.step_after > self.step_before
        )


@dataclass
class RunReplay:
    run_dir: Path
    calls: list[Call]
    states: list[dict]
    task_language: str
    terminated: bool
    sandbox: dict
    finish: dict | None
    stats: dict
    model: str
    warnings: list[str] = field(default_factory=list)

    def state_at(self, step: int | None) -> dict:
        for entry in self.states:
            if entry.get("step_idx") == step:
                return entry
        return {}


def _load_json_docs(path: Path) -> list[dict]:
    """Read a file that may hold several concatenated JSON documents.

    The transcript is opened in append mode, so a resumed session leaves more
    than one document in the file.
    """
    text = path.read_text()
    docs: list[dict] = []
    decoder = json.JSONDecoder()
    pos = 0
    while pos < len(text):
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos >= len(text):
            break
        doc, end = decoder.raw_decode(text, pos)
        docs.append(doc)
        pos = end
    return docs


def _transcript(run_dir: Path, warnings: list[str]) -> dict:
    candidates = sorted(run_dir.glob("transcript_*.json"))
    if not candidates:
        warnings.append("no transcript_*.json — timeline has calls but no reasoning")
        return {}
    if len(candidates) > 1:
        warnings.append(f"multiple transcripts, using {candidates[0].name}")
    docs = _load_json_docs(candidates[0])
    if len(docs) > 1:
        warnings.append(
            f"{candidates[0].name} holds {len(docs)} appended sessions; joining all"
        )
        merged = dict(docs[-1])
        merged["messages"] = [m for d in docs for m in d.get("messages", [])]
        return merged
    return docs[0] if docs else {}


def _attach_reasoning(calls: list[Call], messages: list[dict], warnings: list[str]) -> None:
    i = 0
    turn = 0
    for message in messages:
        if message.get("role") != "assistant":
            continue
        turn += 1
        content = message.get("content")
        texts: list[str] = []
        tool_uses: list[dict] = []
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    texts.append(str(block.get("text") or ""))
                elif block.get("type") == "tool_use":
                    tool_uses.append(block)
        reasoning = "\n".join(t for t in texts if t.strip()).strip()
        for block in tool_uses:
            if i >= len(calls):
                warnings.append(
                    "transcript has more tool_use blocks than logged calls"
                )
                return
            call = calls[i]
            if block.get("name") and block["name"] != call.tool:
                warnings.append(
                    f"seq {call.seq}: transcript says {block['name']!r}, "
                    f"log says {call.tool!r} — positional join may be off here"
                )
            call.reasoning = reasoning
            call.turn = turn
            reasoning = ""  # a turn's text belongs to its first call only
            i += 1
    if i < len(calls):
        warnings.append(f"{len(calls) - i} logged calls have no transcript turn")


def load_run(run_dir: str | Path) -> RunReplay:
    run_dir = Path(run_dir)
    warnings: list[str] = []

    records = tool_log.load(run_dir)
    calls = [
        Call(
            seq=r.get("seq", i + 1),
            tool=str(r.get("tool", "?")),
            args=r.get("args") or {},
            status=str(r.get("status", "?")),
            elapsed_s=r.get("elapsed_s"),
            step_before=r.get("step_idx_before"),
            step_after=r.get("step_idx_after"),
            result=r.get("result"),
        )
        for i, r in enumerate(records)
    ]
    if not calls:
        warnings.append("tool_calls.jsonl missing or empty")

    states_path = run_dir / "states.json"
    states: list[dict] = []
    if states_path.exists():
        try:
            states = [e for e in json.loads(states_path.read_text()) if isinstance(e, dict)]
        except Exception as exc:
            warnings.append(f"states.json unreadable: {exc}")
    else:
        warnings.append("states.json missing")

    transcript = _transcript(run_dir, warnings)
    _attach_reasoning(calls, transcript.get("messages", []), warnings)

    sandbox: dict = {}
    sandbox_path = run_dir / "sandbox.json"
    if sandbox_path.exists():
        try:
            sandbox = json.loads(sandbox_path.read_text())
        except Exception as exc:
            warnings.append(f"sandbox.json unreadable: {exc}")
    else:
        warnings.append("sandbox.json missing (pre-sandbox run)")

    task_language = ""
    for entry in states:
        lang = entry.get("task_language") or (entry.get("state") or {}).get("task_language")
        if lang:
            task_language = str(lang)
            break

    terminated = any(
        entry.get("libero_terminated")
        or (entry.get("result") or {}).get("libero_terminated")
        for entry in states
    )

    return RunReplay(
        run_dir=run_dir,
        calls=calls,
        states=states,
        task_language=task_language,
        terminated=terminated,
        sandbox=sandbox,
        finish=transcript.get("finish"),
        stats=transcript.get("stats") or {},
        model=str(transcript.get("model", "")),
        warnings=warnings,
    )
