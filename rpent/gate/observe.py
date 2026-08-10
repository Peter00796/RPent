"""Level 1 of the digestion: per-run observations. LIBRARY-BLIND by design.

The observer replays one run's record in a fresh context — it sees exactly
what the run recorded (including which memory entries the run itself read)
and nothing else, so ten observers over ten runs produce INDEPENDENT
accounts, and the same lesson surfacing in seven of them is real support
rather than one synthesizer repeating itself.

Observations state facts about THIS run only, each grounded in citation
tokens. Generalization ("always", "should", "in every scene") is the
synthesizer's job, one level up.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from rpent.replay.loader import RunReplay, load_run

OBSERVE_SYSTEM = """You are the run observer for a robot-manipulation harness.
You are given the complete evidence record of ONE finished run. Write 1-6
OBSERVATIONS: factual statements about what happened in THIS run.

Rules, all hard:
- Every observation cites the record: tokens like run:<run>#seq=N (a tool
  call) or run:<run>#step=N (an env step). A statement you cannot cite, you
  do not write.
- THIS RUN ONLY. No generalization: never "always", "should", "in every
  scene". You are a witness, not a theorist.
- Numbers only if they appear in a cited record.
- Prefer observations that explain the run's outcome: what worked, what
  failed, what was tried repeatedly, what was consulted and whether it
  helped.
- CONTRAST PAIRS ARE THE MOST VALUABLE OBSERVATION TYPE. If the run tried
  the same subgoal more than one way (a different prompt, pre-position,
  approach, or height), you MUST write a contrast observation: which
  variant worked, which failed, citing every attempt. State the difference
  in RELATIVE terms that survive a re-randomised scene (offsets from
  measured features like a rim centre or an object top), never as absolute
  coordinates.

Output format — repeat this block per observation, nothing else:

===OBSERVATION===
---
claim: <one factual sentence>
evidence:
  - cite: run:<run_dir_name>#seq=<n>
    role: <what this citation shows>
---
<2-4 sentences of detail, still this-run-only, still cited.>
"""


def run_digest(run_dir: Path, max_chars: int = 60000) -> tuple[str, RunReplay]:
    """A compact, citation-ready text account of the run, from the record."""
    run = load_run(run_dir)
    name = run.run_dir.name
    lines = [
        f"RUN {name}",
        f"task: {run.task_language}",
        f"outcome: {'TERMINATED (success)' if run.terminated else 'NOT terminated'}",
        f"finish: {json.dumps(run.finish) if run.finish else 'none'}",
        f"sandbox profile: {(run.sandbox or {}).get('profile', '?')}",
        "",
    ]
    by_seq = {c.seq: c for c in run.calls}
    for turn in run.turns:
        lines.append(f"-- turn {turn.index} --")
        for kind, value in turn.segments:
            if kind == "text":
                text = re.sub(r"\s+", " ", str(value)).strip()
                lines.append(f"  [says] {text[:400]}")
                continue
            call = by_seq.get(value)
            if call is None:
                continue
            result_brief = json.dumps(call.result, default=str)[:300]
            args_brief = json.dumps(call.args, default=str)[:150]
            advanced = " ENV-STEP" if call.advanced else ""
            lines.append(
                f"  [run:{name}#seq={call.seq}]{advanced} {call.tool}({args_brief}) "
                f"-> {call.status} {result_brief}"
            )
    digest = "\n".join(lines)
    if len(digest) > max_chars:
        digest = digest[:max_chars] + "\n[digest truncated]"
    return digest, run


def split_blocks(text: str, delimiter: str) -> list[str]:
    """Chunks between delimiter lines, whitespace-trimmed, empties dropped."""
    parts = re.split(rf"^\s*{re.escape(delimiter)}\s*$", text, flags=re.M)
    return [p.strip() for p in parts if p.strip()]


def observe_run(run_dir: Path, model: str, base_url: str | None = None) -> list[Path]:
    """Write ``{run_dir}/observations/obs_NN.md``; returns the paths."""
    from langchain.chat_models import init_chat_model

    digest, _ = run_digest(Path(run_dir))
    kwargs = {"base_url": base_url} if base_url else {}
    chat = init_chat_model(model, **kwargs)
    reply = chat.invoke([("system", OBSERVE_SYSTEM), ("user", digest)])
    text = reply.content if isinstance(reply.content, str) else json.dumps(reply.content)

    out_dir = Path(run_dir) / "observations"
    out_dir.mkdir(exist_ok=True)
    written: list[Path] = []
    for i, block in enumerate(split_blocks(text, "===OBSERVATION==="), 1):
        path = out_dir / f"obs_{i:02d}.md"
        path.write_text(block + "\n")
        written.append(path)
    return written
