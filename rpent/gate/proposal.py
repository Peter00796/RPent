"""The proposal contract: YAML frontmatter + a technique body.

A proposal with no parseable evidence dies at the contract check without
its content being read — provenance is a mechanism here, not a request.

    ---
    title: pre-position above the measured top surface before pi0_pick
    action: add | revise | evict | endorse
    type: technique | invariant | failure_mode
    scope: common | env
    conditions: upright objects; skip when yaw_is_meaningful=false
    target: memory/libero/xxx.md        # revise/evict/endorse only
    evidence:
      - cite: run:<run_dir>#seq=17
        role: measurement
    counter_evidence: []                # honest field: where it did not work
    ---
    (body: technique in admission-rule language — which primitive, which
    order, which failure mode; never a value)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rpent.gate.tokens import Cite, parse_cite

ACTIONS = ("add", "revise", "evict", "endorse")
TYPES = ("technique", "invariant", "failure_mode")
SCOPES = ("common", "env")
#: Actions that touch an existing entry — higher evidence bar, target required.
TARGETED_ACTIONS = ("revise", "evict", "endorse")


@dataclass
class Evidence:
    cite_raw: str
    role: str
    cite: Cite | None


@dataclass
class Proposal:
    path: Path
    title: str = ""
    action: str = ""
    type: str = ""
    scope: str = ""
    conditions: str = ""
    target: str = ""
    evidence: list[Evidence] = field(default_factory=list)
    counter_evidence: list[Evidence] = field(default_factory=list)
    support: int | None = None
    body: str = ""
    contract_errors: list[str] = field(default_factory=list)

    @property
    def cited_runs(self) -> set[str]:
        return {e.cite.run for e in self.evidence if e.cite is not None}


def _split_frontmatter(text: str) -> tuple[str, str] | None:
    """(frontmatter, body) for a ``---`` fenced file, else None.

    Only the FIRST closing fence ends the frontmatter, so a body that
    contains ``---`` lines survives intact.
    """
    if not text.startswith("---"):
        return None
    rest = text[3:]
    if rest.startswith("\n"):
        rest = rest[1:]
    closing = rest.find("\n---")
    if closing == -1:
        return None
    front = rest[:closing]
    body = rest[closing + 4:]
    if body.startswith("\n"):
        body = body[1:]
    return front, body


def _evidence_list(raw, errors: list[str], label: str) -> list[Evidence]:
    out: list[Evidence] = []
    if raw is None:
        return out
    if not isinstance(raw, list):
        errors.append(f"{label} must be a list")
        return out
    for item in raw:
        if isinstance(item, str):
            item = {"cite": item, "role": ""}
        if not isinstance(item, dict) or "cite" not in item:
            errors.append(f"{label} item missing 'cite': {item!r}")
            continue
        cite = parse_cite(str(item["cite"]))
        if cite is None:
            errors.append(f"{label} cite does not parse: {item['cite']!r}")
        out.append(Evidence(cite_raw=str(item["cite"]),
                            role=str(item.get("role", "")), cite=cite))
    return out


def load_proposal(path: str | Path) -> Proposal:
    """Parse one proposal file; contract violations collect, never raise."""
    import yaml

    path = Path(path)
    proposal = Proposal(path=path)
    errors = proposal.contract_errors

    try:
        text = path.read_text()
    except OSError as exc:
        errors.append(f"unreadable: {exc}")
        return proposal

    split = _split_frontmatter(text)
    if split is None:
        errors.append("no YAML frontmatter (--- ... ---)")
        proposal.body = text.strip()
        return proposal
    front_text, proposal.body = split[0], split[1].strip()

    try:
        front = yaml.safe_load(front_text) or {}
    except Exception as exc:
        errors.append(f"frontmatter is not valid YAML: {exc}")
        return proposal
    if not isinstance(front, dict):
        errors.append("frontmatter is not a mapping")
        return proposal

    proposal.title = str(front.get("title", "")).strip()
    proposal.action = str(front.get("action", "")).strip()
    proposal.type = str(front.get("type", "")).strip()
    proposal.scope = str(front.get("scope", "")).strip()
    proposal.conditions = str(front.get("conditions", "") or "").strip()
    proposal.target = str(front.get("target", "") or "").strip()
    if front.get("support") is not None:
        try:
            proposal.support = int(front["support"])
        except (TypeError, ValueError):
            errors.append(f"support is not an integer: {front['support']!r}")

    if not proposal.title:
        errors.append("missing title")
    if proposal.action not in ACTIONS:
        errors.append(f"action must be one of {ACTIONS}, got {proposal.action!r}")
    if proposal.type not in TYPES:
        errors.append(f"type must be one of {TYPES}, got {proposal.type!r}")
    if proposal.scope not in SCOPES:
        errors.append(f"scope must be one of {SCOPES}, got {proposal.scope!r}")
    if proposal.action in TARGETED_ACTIONS and not proposal.target:
        errors.append(f"action {proposal.action!r} requires a target entry path")
    if proposal.action == "add" and proposal.target:
        errors.append("action 'add' must not carry a target")

    proposal.evidence = _evidence_list(front.get("evidence"), errors, "evidence")
    proposal.counter_evidence = _evidence_list(
        front.get("counter_evidence"), errors, "counter_evidence")
    if not proposal.evidence:
        errors.append("no evidence — a proposal without citations is not read")

    unknown = set(front) - {"title", "action", "type", "scope", "conditions",
                            "target", "evidence", "counter_evidence", "support"}
    if unknown:
        errors.append(f"unknown frontmatter keys: {sorted(unknown)}")
    return proposal


def collect_proposals(run_dirs: list[Path],
                      proposal_dirs: list[Path] = ()) -> list[Proposal]:
    """Proposals under the runs' ``memory_proposals``/``proposals`` dirs,
    plus any extra dirs of ``*.md`` (e.g. a synthesizer's output)."""
    out: list[Proposal] = []
    for run_dir in run_dirs:
        for sub in ("memory_proposals", "proposals"):
            for path in sorted(Path(run_dir).glob(f"{sub}/*.md")):
                out.append(load_proposal(path))
    for directory in proposal_dirs:
        for path in sorted(Path(directory).glob("*.md")):
            out.append(load_proposal(path))
    return out
