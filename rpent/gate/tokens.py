"""Citation tokens: the one grammar every evidence reference uses.

    run:<run_dir_name>#seq=17      one tool call   -> tool_calls.jsonl record
    run:<run_dir_name>#step=5      one env step    -> states.json entry
    run:<run_dir_name>/<relpath>   one artifact    -> file under the run dir

Humans, proposals, gate reports and the replay pages all speak this form;
:func:`resolve` dereferences a token against the run archive and returns
what is actually recorded there, plus the ``replay.html`` deep link.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from rpent.tools import tool_log


def run_map(run_dirs) -> dict[str, Path]:
    """name -> run dir, for resolving ``run:<name>`` against a given set."""
    return {Path(d).name: Path(d) for d in run_dirs}

_CITE_RE = re.compile(
    r"^run:(?P<run>[^#/]+)(?:#(?P<kind>seq|step)=(?P<num>\d+)|/(?P<path>.+))$"
)


@dataclass(frozen=True)
class Cite:
    raw: str
    run: str
    kind: str            # "seq" | "step" | "path"
    value: object        # int for seq/step, str relpath for path


def parse_cite(text: str) -> Cite | None:
    m = _CITE_RE.match(str(text).strip())
    if not m:
        return None
    if m.group("kind"):
        return Cite(raw=text, run=m.group("run"), kind=m.group("kind"),
                    value=int(m.group("num")))
    return Cite(raw=text, run=m.group("run"), kind="path", value=m.group("path"))


@dataclass
class Resolved:
    cite: Cite
    exists: bool
    summary: str = ""            # one line of what the record actually says
    record: dict | None = None   # the raw record, for deeper checks
    replay_href: str = ""        # relative to the run dir


def resolve(cite: Cite, runs: Mapping[str, Path]) -> Resolved:
    run_dir = runs.get(cite.run)
    if run_dir is None or not Path(run_dir).is_dir():
        return Resolved(cite=cite, exists=False, summary=f"run dir not found: {cite.run}")
    run_dir = Path(run_dir)

    if cite.kind == "seq":
        for record in tool_log.load(run_dir):
            if record.get("seq") == cite.value:
                result = record.get("result")
                brief = json.dumps(result, default=str)[:160] if result is not None else ""
                return Resolved(
                    cite=cite, exists=True, record=record,
                    summary=f"{record.get('tool')}({json.dumps(record.get('args'), default=str)[:80]}) "
                            f"-> {record.get('status')} {brief}",
                    replay_href=f"replay.html#seq-{cite.value}",
                )
        return Resolved(cite=cite, exists=False,
                        summary=f"seq {cite.value} not in tool_calls.jsonl")

    if cite.kind == "step":
        states_path = run_dir / "states.json"
        if states_path.exists():
            try:
                states = json.loads(states_path.read_text())
            except Exception as exc:
                return Resolved(cite=cite, exists=False, summary=f"states.json unreadable: {exc}")
            for entry in states:
                if isinstance(entry, dict) and entry.get("step_idx") == cite.value:
                    cmd = entry.get("command") or {}
                    return Resolved(
                        cite=cite, exists=True, record=entry,
                        summary=f"step {cite.value}: {cmd.get('action') or 'state'}",
                        replay_href=f"replay.html#step-{cite.value}",
                    )
        return Resolved(cite=cite, exists=False, summary=f"step {cite.value} not in states.json")

    target = run_dir / str(cite.value)
    return Resolved(
        cite=cite, exists=target.exists(),
        summary=str(cite.value) if target.exists() else f"artifact missing: {cite.value}",
    )
