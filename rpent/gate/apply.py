"""Execute the human-edited verdicts: the only writer of the memory library.

Four verbs:

- ``add``      -> new entry at the destination, provenance stamped;
- ``revise``   -> target's body replaced, its history appended, never edited;
- ``evict``    -> target moved to ``memory/evicted/`` with the reason — an
                  eviction is a negative result, so it is archived, not erased;
- ``endorse``  -> target's support incremented, endorsement recorded.

Anything not ``admit`` is only logged (with reasons) into decisions.yaml
beside the verdicts file. The returned summary is written for a commit
message: one library commit per applied batch = one generation.
"""
from __future__ import annotations

import datetime
from pathlib import Path

from rpent.gate.proposal import Proposal, load_proposal


def _split_entry(text: str) -> tuple[dict, str]:
    import yaml

    if text.startswith("---"):
        rest = text[3:].lstrip("\n")
        closing = rest.find("\n---")
        if closing != -1:
            front = yaml.safe_load(rest[:closing]) or {}
            body = rest[closing + 4:].lstrip("\n")
            return (front if isinstance(front, dict) else {}), body
    return {}, text


def _dump_entry(front: dict, body: str) -> str:
    import yaml

    return f"---\n{yaml.safe_dump(front, allow_unicode=True, sort_keys=False)}---\n\n{body}\n"


def _provenance(p: Proposal, batch: str) -> dict:
    return {
        "action": p.action,
        "proposal": str(p.path),
        "batch": batch,
        "date": datetime.date.today().isoformat(),
        "evidence": [e.cite_raw for e in p.evidence],
        "counter_evidence": [e.cite_raw for e in p.counter_evidence],
    }


def _apply_one(p: Proposal, destination: str, memory_root: Path, batch: str) -> str:
    repo_side = Path(memory_root).parent
    if p.action == "add":
        dest = repo_side / destination
        if dest.exists():
            return f"SKIPPED add {destination}: already exists (use revise/endorse)"
        dest.parent.mkdir(parents=True, exist_ok=True)
        front = {
            "title": p.title, "type": p.type, "scope": p.scope,
            "conditions": p.conditions or None,
            "support": max(len(p.cited_runs), 1),
            "provenance": [_provenance(p, batch)],
        }
        dest.write_text(_dump_entry({k: v for k, v in front.items() if v is not None},
                                    p.body))
        return f"added {destination} (support {front['support']})"

    target = repo_side / p.target
    if not target.exists():
        return f"SKIPPED {p.action} {p.target}: target missing"
    front, body = _split_entry(target.read_text())
    front.setdefault("provenance", []).append(_provenance(p, batch))

    if p.action == "revise":
        if p.conditions:
            front["conditions"] = p.conditions
        target.write_text(_dump_entry(front, p.body or body))
        return f"revised {p.target}"

    if p.action == "endorse":
        front["support"] = int(front.get("support", 1)) + max(len(p.cited_runs), 1)
        target.write_text(_dump_entry(front, body))
        return f"endorsed {p.target} (support -> {front['support']})"

    if p.action == "evict":
        evicted_dir = Path(memory_root) / "evicted"
        evicted_dir.mkdir(parents=True, exist_ok=True)
        grave = evicted_dir / target.name
        front["evicted"] = datetime.date.today().isoformat()
        grave.write_text(_dump_entry(front, body))
        target.unlink()
        return f"evicted {p.target} -> memory/evicted/{target.name}"

    return f"SKIPPED {p.path}: unknown action {p.action!r}"


def apply_verdicts(verdicts_path: str | Path, memory_root: str | Path) -> str:
    """Apply every ``verdict: admit``; log the rest. Returns the summary."""
    import yaml

    verdicts_path = Path(verdicts_path)
    memory_root = Path(memory_root)
    items = yaml.safe_load(verdicts_path.read_text()) or []
    batch = verdicts_path.parent.name or verdicts_path.stem

    applied: list[str] = []
    skipped: list[dict] = []
    for item in items:
        verdict = str(item.get("verdict", "")).strip()
        if verdict != "admit":
            skipped.append({"proposal": item.get("proposal"),
                            "verdict": verdict or "(none)",
                            "reasons": item.get("reasons", [])})
            continue
        p = load_proposal(item["proposal"])
        if p.contract_errors:
            applied.append(f"SKIPPED {p.path}: contract errors {p.contract_errors}")
            continue
        applied.append(_apply_one(p, str(item.get("destination", "")), memory_root, batch))

    decisions_path = verdicts_path.parent / "decisions.yaml"
    decisions_path.write_text(yaml.safe_dump(
        {"applied": applied, "not_applied": skipped},
        allow_unicode=True, sort_keys=False))

    lines = [f"gate: {len(applied)} applied, {len(skipped)} held/rejected "
             f"(batch {batch})", *[f"  - {a}" for a in applied]]
    for s in skipped:
        lines.append(f"  - {s['verdict']}: {s['proposal']}")
    return "\n".join(lines)
