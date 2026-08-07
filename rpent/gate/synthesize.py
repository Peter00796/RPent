"""Level 2 of the digestion: sweep-wide synthesis, with the library in view.

The synthesizer reads every run's observations plus the outcome table, the
CURRENT library, and the consultation ledger — and answers, per issue
cluster, the triage question:

    does an existing entry cover this?
      no                       -> propose add
      yes, but never consulted -> discoverability: revise title/conditions
      yes, consulted, failed   -> revise content (cite where it failed)
      yes, consulted, helped   -> endorse
      refuted by measurement   -> evict

Two outputs, two audiences: proposals/*.md go through the gate's checks and
the human's verdicts; HARNESS_REVIEW.md is the memo for the human — the
diagnosis that does not fit a memory entry (prompt behaviour, tool gaps,
gate tuning) and becomes code PRs, never library writes.

Iron rule, restated in the prompt: proposal evidence cites run records
(``run:<name>#seq=N``), NEVER observation files. Observations are an index,
not evidence.
"""
from __future__ import annotations

import json
from pathlib import Path

from rpent.gate.ledger import scan as ledger_scan
from rpent.gate.observe import split_blocks

SYNTH_SYSTEM = """You are the harness synthesizer for a robot-manipulation
research system. You receive: (1) per-run OBSERVATIONS from a sweep, with the
outcome of every run, (2) the CURRENT memory library, (3) the consultation
LEDGER (which entries runs actually read, and how those runs ended).

Your job: cluster the observations into issues, run each cluster through the
triage — no covering entry -> add; entry exists but was never consulted ->
revise its title/conditions for discoverability; consulted but failed ->
revise its content; consulted and helped -> endorse; refuted -> evict — and
produce library PROPOSALS plus one HARNESS REVIEW memo.

Hard rules:
- Evidence cites run records only: run:<run_dir_name>#seq=N or #step=N.
  NEVER cite observation files — they are an index, not evidence.
- A cross-run claim needs citations from EVERY run it claims (support is
  counted from distinct cited runs, not declared).
- Library entries carry TECHNIQUE (which primitive, which order, which
  failure mode), never values. A number is admissible only as a measured
  range with its citation. Anything identifying one cell's answer (a scene
  object instance, a coordinate) is forbidden.
- scope: common = transferable across environments; env = this environment.
- revise/evict/endorse must name target: (the entry's path) and cite records
  showing the entry was consumed and failed / helped / was refuted.
- What does not fit a memory entry (prompt behaviour, missing tool
  capability, gate tuning) goes in the memo, not in a proposal.

Output format, nothing else:

===PROPOSAL===
---
title: <short imperative>
action: add | revise | evict | endorse
type: technique | invariant | failure_mode
scope: common | env
conditions: <when it applies / when not>
target: <memory/... path, only for revise/evict/endorse>
evidence:
  - cite: run:<run_dir_name>#seq=<n>
    role: <what it shows>
counter_evidence: []
---
<body: the technique, in admission-rule language>

(repeat ===PROPOSAL=== per proposal, then exactly once:)

===HARNESS_REVIEW===
<the memo to the human: issue clusters, what the library cannot fix, each
point cited>
"""


def _outcome_table(run_dirs: list[Path]) -> str:
    import json as _json

    rows = []
    for run_dir in map(Path, run_dirs):
        terminated = None
        states_path = run_dir / "states.json"
        if states_path.exists():
            try:
                states = _json.loads(states_path.read_text())
                terminated = any(
                    e.get("libero_terminated")
                    or (e.get("result") or {}).get("libero_terminated")
                    for e in states if isinstance(e, dict)
                )
            except Exception:
                pass
        rows.append(f"  {run_dir.name}: "
                    f"{'SUCCESS' if terminated else 'FAIL' if terminated is not None else '?'}")
    return "\n".join(rows)


def _library_text(memory_root: Path, max_chars: int = 30000) -> str:
    chunks = []
    for path in sorted(Path(memory_root).rglob("*.md")):
        if path.name == "README.md" or "evicted" in path.parts:
            continue
        rel = path.relative_to(Path(memory_root).parent)
        chunks.append(f"### {rel}\n{path.read_text()}")
    text = "\n\n".join(chunks) or "(the library is empty)"
    if len(text) > max_chars:
        text = text[:max_chars] + "\n[library truncated]"
    return text


def build_synthesis_input(run_dirs: list[Path], memory_root: Path,
                          max_chars: int = 120000) -> str:
    observations = []
    for run_dir in map(Path, run_dirs):
        for path in sorted(Path(run_dir).glob("observations/*.md")):
            observations.append(f"--- from {Path(run_dir).name} ---\n{path.read_text()}")
    ledger = ledger_scan(list(map(Path, run_dirs)), memory_root)
    text = (
        "SWEEP OUTCOMES\n" + _outcome_table(run_dirs)
        + "\n\nOBSERVATIONS\n" + ("\n\n".join(observations) or "(none written)")
        + "\n\nCURRENT LIBRARY\n" + _library_text(memory_root)
        + "\n\nCONSULTATION LEDGER\n"
        + json.dumps({"entries": ledger["entries"],
                      "zombies": ledger["zombies"]}, indent=1, default=str)
    )
    if len(text) > max_chars:
        text = text[:max_chars] + "\n[input truncated]"
    return text


def synthesize(run_dirs: list[Path], memory_root: Path, out_dir: Path,
               model: str, base_url: str | None = None) -> dict:
    """Write ``{out_dir}/proposals/*.md`` + ``{out_dir}/HARNESS_REVIEW.md``."""
    from langchain.chat_models import init_chat_model

    payload = build_synthesis_input(run_dirs, Path(memory_root))
    kwargs = {"base_url": base_url} if base_url else {}
    chat = init_chat_model(model, **kwargs)
    reply = chat.invoke([("system", SYNTH_SYSTEM), ("user", payload)])
    text = reply.content if isinstance(reply.content, str) else json.dumps(reply.content)

    out_dir = Path(out_dir)
    proposals_dir = out_dir / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)

    memo = ""
    if "===HARNESS_REVIEW===" in text:
        text, memo = text.split("===HARNESS_REVIEW===", 1)
    proposals = split_blocks(text, "===PROPOSAL===")
    written = []
    for i, block in enumerate(proposals, 1):
        path = proposals_dir / f"proposal_{i:02d}.md"
        path.write_text(block + "\n")
        written.append(path)
    memo_path = out_dir / "HARNESS_REVIEW.md"
    memo_path.write_text(memo.strip() + "\n" if memo.strip() else
                         "(the synthesizer wrote no memo)\n")
    return {"proposals": written, "memo": memo_path}
