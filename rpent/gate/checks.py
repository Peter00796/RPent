"""The five gate checks. Mechanical where possible, flagged for the human
where not — a flag is a question addressed to the reviewer, never silently
resolved by the code.

Levels: ``reject`` (contract broken — the proposal cannot be evaluated),
``flag`` (needs the reviewer's eye), ``ok`` (informational pass note).
Suggested verdicts: any reject -> reject; any flag -> hold; else admit.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from rpent.gate import tokens
from rpent.gate.proposal import Proposal, TARGETED_ACTIONS

#: Numbers below this, when integers, are treated as prose ("2-3 waypoints")
#: rather than measurements; decimals are always checked.
_INT_LINT_MIN = 10

_NUMBER_RE = re.compile(r"(?<![\w.\-])-?\d+(?:\.\d+)?(?![\w])")
_INSTANCE_RE = re.compile(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)*_\d+)\b")


@dataclass
class Finding:
    check: str
    level: str          # "reject" | "flag" | "ok"
    message: str


@dataclass
class Review:
    proposal: Proposal
    findings: list[Finding] = field(default_factory=list)
    resolutions: list[tokens.Resolved] = field(default_factory=list)
    destination: str = ""

    @property
    def suggested(self) -> str:
        levels = {f.level for f in self.findings}
        if "reject" in levels:
            return "reject"
        if "flag" in levels:
            return "hold"
        return "admit"

    def add(self, check: str, level: str, message: str) -> None:
        self.findings.append(Finding(check=check, level=level, message=message))


def _slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return slug[:60] or "untitled"


def _prose(p: Proposal) -> str:
    return "\n".join((p.title, p.conditions, p.body))


def _record_numbers(resolutions: list[tokens.Resolved]) -> list[float]:
    numbers: list[float] = []
    for r in resolutions:
        if r.record is None:
            continue
        for m in _NUMBER_RE.finditer(json.dumps(r.record, default=str)):
            try:
                numbers.append(float(m.group(0)))
            except ValueError:
                pass
    return numbers


def _matches_measurement(value: float, text: str, measured: list[float]) -> bool:
    """True when ``value`` reads as a rounding of some measured number."""
    decimals = len(text.split(".")[1]) if "." in text else 0
    tolerance = max(1e-9, 0.5 * 10 ** (-decimals))
    return any(abs(value - m) <= tolerance for m in measured)


def _library_entries(memory_root: Path) -> list[Path]:
    return [p for p in sorted(Path(memory_root).rglob("*.md"))
            if p.name not in ("README.md",) and "evicted" not in p.parts]


def _token_set(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9_]+", text.lower()) if len(w) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _object_names(resolutions: list[tokens.Resolved],
                  runs: dict[str, Path]) -> set[str]:
    names: set[str] = set()
    for run_dir in {runs[r.cite.run] for r in resolutions if r.cite.run in runs}:
        states_path = Path(run_dir) / "states.json"
        if not states_path.exists():
            continue
        try:
            states = json.loads(states_path.read_text())
        except Exception:
            continue
        for entry in states:
            if isinstance(entry, dict):
                state = entry.get("state") or entry
                for name in state.get("object_names") or []:
                    names.add(str(name))
    return names


def run_checks(
    p: Proposal,
    runs: dict[str, Path],
    memory_root: Path,
    env_name: str,
    batch: list[Proposal],
) -> Review:
    review = Review(proposal=p)
    prose = _prose(p)

    # -- 1. contract --------------------------------------------------------
    for error in p.contract_errors:
        review.add("contract", "reject", error)
    for ev in (*p.evidence, *p.counter_evidence):
        if ev.cite is None:
            continue  # already a contract error
        resolved = tokens.resolve(ev.cite, runs)
        review.resolutions.append(resolved)
        if not resolved.exists:
            review.add("contract", "reject",
                       f"cite does not resolve: {ev.cite_raw} — {resolved.summary}")
    if p.action in TARGETED_ACTIONS and p.target:
        target_path = Path(memory_root).parent / p.target
        if not target_path.exists():
            review.add("contract", "reject", f"target entry not found: {p.target}")
        elif p.action in ("revise", "evict"):
            review.add("contract", "flag",
                       f"{p.action} touches an existing entry — verify the cited "
                       "records show it was CONSUMED and still failed/refuted")

    if review.suggested == "reject":
        return review  # unevaluable; the other checks would just add noise

    # -- 2. numbers must trace to cited measurements -------------------------
    measured = _record_numbers(review.resolutions)
    for m in _NUMBER_RE.finditer(prose):
        text = m.group(0)
        value = float(text)
        if "." not in text and abs(value) < _INT_LINT_MIN:
            continue
        if _matches_measurement(value, text, measured):
            review.add("numbers", "ok", f"{text}: traces to a cited record")
        else:
            review.add("numbers", "flag",
                       f"{text}: not found in any cited record — either cite the "
                       "measurement or delete the number")

    # -- 3. per-cell answers --------------------------------------------------
    object_names = _object_names(review.resolutions, runs)
    for hit in sorted(set(_INSTANCE_RE.findall(prose)) & object_names):
        review.add("cell_answers", "flag",
                   f"names a scene instance ({hit!r}) — a library entry that "
                   "identifies one cell's object is an answer, not knowledge")

    # -- 4. scope -------------------------------------------------------------
    if p.scope == "common":
        vocabulary = {env_name.lower(), "libero"}
        vocabulary |= {re.sub(r"_\d+$", "", n).lower() for n in object_names}
        hits = sorted(v for v in vocabulary if v and re.search(rf"\b{re.escape(v)}\b",
                                                               prose.lower()))
        if hits:
            review.add("scope", "flag",
                       f"claims scope=common but mentions {hits} — likely scope=env")

    # -- 5. dedup / merge ------------------------------------------------------
    own = _token_set(prose)
    for entry in _library_entries(memory_root):
        similarity = _jaccard(own, _token_set(entry.read_text()))
        if similarity >= 0.5 and str(entry) != str(Path(memory_root).parent / p.target or ""):
            review.add("dedup", "flag",
                       f"{similarity:.0%} similar to library entry "
                       f"{entry.relative_to(Path(memory_root).parent)} — consider "
                       "endorse/revise instead of add")
    for other in batch:
        if other.path == p.path:
            continue
        similarity = _jaccard(own, _token_set(_prose(other)))
        if similarity >= 0.7:
            review.add("dedup", "flag",
                       f"{similarity:.0%} similar to batch proposal "
                       f"{other.path.name} — merge and count support")

    # -- support count vs distinct cited runs ---------------------------------
    if p.support is not None and p.support != len(p.cited_runs):
        review.add("contract", "flag",
                   f"claims support={p.support} but cites {len(p.cited_runs)} "
                   "distinct runs — support is counted, not declared")

    review.destination = (p.target if p.action in TARGETED_ACTIONS else
                          f"memory/{'common' if p.scope == 'common' else env_name}"
                          f"/{_slug(p.title)}.md")
    return review
