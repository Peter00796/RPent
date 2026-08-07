"""The consultation ledger: what the library actually did in the field.

Consumption is read MECHANICALLY from ``tool_calls.jsonl`` — a memory entry
was consulted iff a successful ``read_text_file`` returned a path under the
memory root — never from the agent's own strategy notes. Crossed with each
run's outcome this gives every entry a track record, and three grounds for
leaving the library:

- refuted     -> evict now (handled as an ``evict`` proposal with the cite);
- negative    -> consulted repeatedly, runs keep failing: review;
- zombie      -> present for generations, never consulted: retire.

The ledger only reports; removal decisions go through the same verdict flow
as admissions.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from rpent.tools import tool_log


def _terminated(run_dir: Path) -> bool | None:
    states_path = run_dir / "states.json"
    if not states_path.exists():
        return None
    try:
        states = json.loads(states_path.read_text())
    except Exception:
        return None
    return any(
        e.get("libero_terminated") or (e.get("result") or {}).get("libero_terminated")
        for e in states if isinstance(e, dict)
    )


def _memory_rel(path: str) -> str | None:
    """'…/memory/libero/x.md' -> 'memory/libero/x.md', else None."""
    m = re.search(r"(?:^|/)(memory/.+)$", str(path))
    return m.group(1) if m else None


def scan(run_dirs: list[Path], memory_root: Path) -> dict:
    """Aggregate consumption per entry across the given runs."""
    entries: dict[str, dict] = {}
    runs_seen = 0
    for run_dir in map(Path, run_dirs):
        records = tool_log.load(run_dir)
        if not records:
            continue
        runs_seen += 1
        outcome = _terminated(run_dir)
        for record in records:
            if record.get("tool") != "read_text_file":
                continue
            result = record.get("result")
            if not isinstance(result, dict) or result.get("error"):
                continue
            rel = _memory_rel(result.get("path", ""))
            if rel is None or rel.endswith("README.md"):
                continue
            slot = entries.setdefault(rel, {"reads": 0, "runs": {}})
            slot["reads"] += 1
            slot["runs"][run_dir.name] = bool(outcome)

    for rel, slot in entries.items():
        outcomes = slot["runs"].values()
        slot["consulted_runs"] = len(slot["runs"])
        slot["successes"] = sum(1 for o in outcomes if o)
        slot["failures"] = sum(1 for o in outcomes if not o)

    # Zombies: entries on disk that no scanned run ever consulted.
    on_disk = {
        str(p.relative_to(Path(memory_root).parent))
        for p in Path(memory_root).rglob("*.md")
        if p.name != "README.md" and "evicted" not in p.parts
    }
    zombies = sorted(on_disk - set(entries))

    recommendations = []
    for rel, slot in sorted(entries.items()):
        if slot["consulted_runs"] >= 2 and slot["successes"] == 0:
            recommendations.append(
                f"review {rel}: consulted in {slot['consulted_runs']} runs, "
                "all of which failed"
            )
    for rel in zombies:
        recommendations.append(f"zombie {rel}: never consulted in the scanned runs")

    return {
        "runs_scanned": runs_seen,
        "entries": entries,
        "zombies": zombies,
        "recommendations": recommendations,
    }


def write_ledger(result: dict, memory_root: Path) -> Path:
    out = Path(memory_root) / "LEDGER.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True))
    return out
