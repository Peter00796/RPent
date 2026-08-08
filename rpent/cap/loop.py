"""The out-of-loop coding agent: write → run an episode → debug → freeze.

ASPIRE's cycle (arXiv 2607.00272), on our evidence layer: the coding agent
never lives inside an episode. Each attempt launches a full run under
``--planner program``; the agent then reads the RECORDED evidence — the
run digest (reasoning-free here: pure call/result trail), the program
traceback if any, and the outcome — and revises the program. When a debug
seed passes, the program is frozen (hash recorded); held-out evaluation
runs the frozen file unchanged.

What the agent is given per revision, all from disk:
- the tool API documentation (rendered from tool_docs + schemas — the same
  contract the turn-by-turn planner reads);
- the memory library (transferable technique, the skill-library role);
- every prior attempt's program, outcome, digest and traceback.

Programs are per-cell policy artifacts under ``programs/`` — legitimate via
the seed-split protocol, never via the memory admission rule.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from rpent.utils.config import get_repo_root
from rpent.utils.logging import get_logger

logger = get_logger("cap_loop")

SYNTH_SYSTEM = """You write Python robot-control programs for a manipulation
harness. You are given the task, the exact API available to your program, a
library of transferable technique, and — after the first attempt — the full
evidence record of every prior attempt.

Rules:
- Output exactly ONE fenced python block containing the COMPLETE program.
  It runs top-level (the API functions are globals) and must end by calling
  finish(status, summary). No imports beyond the provided math/json.
- The API is everything you have. Measure, do not assume: every coordinate
  you command must come from a segment/back_project/world_extent result
  computed in the SAME episode the program is running in. Scenes vary
  between episodes, so hardcoded coordinates are bugs by construction —
  write the program to re-derive them each run.
- Check returns. Every call reports status/geometry; a program that ignores
  a failed grasp and carries on is the failure mode this loop exists to fix.
- Prefer simple, verifiable steps: localize -> verify -> act -> verify.
- When revising, read the traceback and the call trail first; change what
  the evidence implicates, not what you feel like rewriting."""


def render_api_doc() -> str:
    """The program-facing API contract, rendered from tool_docs + schemas."""
    from robots.libero.tools import schemas
    from robots.libero.tools.tool_docs import LIBERO_TOOL_DOCS, render_description

    schema_by_tool = {
        "view_driver_state": schemas.ViewDriverStateInput,
        "move_to": schemas.MoveToInput,
        "move_pose": schemas.MovePoseInput,
        "rotate_wrist": schemas.RotateWristInput,
        "rotate_pitch": schemas.RotatePitchInput,
        "release": schemas.ReleaseInput,
        "set_gripper": schemas.SetGripperInput,
        "pi0_pick": schemas.Pi0PickInput,
        "pi0_doubled": schemas.Pi0DoubledInput,
        "view_camera_meta": schemas.ViewCameraMetaInput,
        "segment": schemas.SegmentInput,
        "back_project": schemas.BackProjectInput,
        "world_extent": schemas.WorldExtentInput,
        "compare_extent": schemas.CompareExtentInput,
    }
    lines = ["Each function returns a dict; inspect it. Signatures:"]
    for name, model in schema_by_tool.items():
        args = []
        for field_name, field in model.model_fields.items():
            if field.is_required():
                args.append(field_name)
            else:
                default = field.get_default()
                args.append(f"{field_name}={default!r}")
        lines.append(f"\n### {name}({', '.join(args)})")
        lines.append(render_description(name))
    lines.append("\n### finish(status, summary)")
    lines.append("End the episode. status: 'success' | 'failure' | 'stuck'.")
    return "\n".join(lines)


def _memory_digest(max_chars: int = 12000) -> str:
    root = get_repo_root() / "memory"
    chunks = []
    for path in sorted(root.rglob("*.md")):
        if path.name == "README.md" or "evicted" in path.parts:
            continue
        chunks.append(f"## {path.stem}\n{path.read_text().split('---')[-1].strip()}")
    text = "\n\n".join(chunks) or "(empty)"
    return text[:max_chars]


def _attempt_digest(run_dir: Path, max_chars: int = 25000) -> str:
    from rpent.gate.observe import run_digest

    digest, _ = run_digest(run_dir, max_chars=max_chars)
    err = run_dir / "analysis" / "program_error.txt"
    if err.exists():
        digest += "\n\nPROGRAM TRACEBACK:\n" + err.read_text()[-3000:]
    return digest


def _extract_program(reply: str) -> str | None:
    m = re.findall(r"```python\n(.*?)```", reply, re.DOTALL)
    return m[-1].strip() + "\n" if m else None


def _run_episode(cli_args: list[str], program: Path, out_root: Path) -> Path | None:
    """One episode under --planner program; returns the run dir."""
    cmd = [sys.executable, "-m", "rpent.cli.main", *cli_args,
           "--planner", "program", "--program-file", str(program)]
    logger.info("episode: %s", " ".join(cmd))
    subprocess.run(cmd, check=False)
    runs = sorted(out_root.glob("*_s*"), key=lambda p: p.stat().st_mtime)
    return runs[-1] if runs else None


def _terminated(run_dir: Path) -> bool:
    try:
        states = json.loads((run_dir / "states.json").read_text())
    except Exception:
        return False
    return any(e.get("libero_terminated") or (e.get("result") or {}).get("libero_terminated")
               for e in states if isinstance(e, dict))


def _score(run_dir: Path) -> float:
    """Crude mechanical fitness for candidate selection, from the record only.

    Lexicographic in spirit: solved dominates everything; otherwise more env
    steps advanced beats fewer (a program that acts and fails outranks one
    that dies in perception), and a clean exit beats a traceback. Deliberately
    not a learned or judged score — selection pressure must be as auditable
    as everything else. Refine when the evidence says this misranks.
    """
    if _terminated(run_dir):
        return 1_000_000.0
    try:
        states = [e for e in json.loads((run_dir / "states.json").read_text())
                  if isinstance(e, dict)]
        steps = max((e.get("step_idx", 0) for e in states), default=0)
    except Exception:
        steps = 0
    crashed = (run_dir / "analysis" / "program_error.txt").exists()
    return steps * 10.0 + (0.0 if crashed else 1.0)


def cap_loop(*, suite: str, task: int, debug_seed: int, model: str,
             base_url: str | None, max_attempts: int, logs_root: Path,
             extra_cli: list[str], k: int = 1) -> dict:
    """Rounds of K candidate programs until the debug seed passes.

    ``k=1`` is plain iterative refinement; ``k>1`` is ASPIRE's evolutionary
    search (Algorithm 1): each round proposes K candidates conditioned on the
    top-performing prior programs AND their remaining failure evidence, plus
    this round's earlier siblings with an explicit instruction to explore a
    DISTINCT strategy — single-trajectory refinement gets stuck in one
    solution family; the population is what escapes it. Selection is
    :func:`_score`: mechanical, from the record, auditable.

    ``max_attempts`` counts ROUNDS. Total episodes <= max_attempts * k, each
    a full env boot — on one GPU this is the cost knob that matters.
    """
    from langchain.chat_models import init_chat_model

    programs_dir = get_repo_root() / "programs" / suite / f"t{task}"
    programs_dir.mkdir(parents=True, exist_ok=True)
    chat = init_chat_model(model, **({"base_url": base_url} if base_url else {}))
    api_doc = render_api_doc()
    memory = _memory_digest()

    task_line = (f"suite={suite} task={task} seed={debug_seed} — write a program "
                 "that solves this cell's manipulation task.")
    cli_args = ["--env", "libero", "--suite", suite, "--task", str(task),
                "--seed", str(debug_seed), "--sandbox", "none", *extra_cli]

    #: every evaluated candidate: (score, label, program_source, evidence)
    population: list[tuple[float, str, str, str]] = []
    episodes = 0

    for round_no in range(1, max_attempts + 1):
        siblings: list[str] = []
        for cand in range(1, k + 1):
            label = f"r{round_no:02d}c{cand}"
            parts = [f"TASK\n{task_line}", f"API\n{api_doc}",
                     f"TECHNIQUE LIBRARY\n{memory}"]
            parents = sorted(population, key=lambda p: -p[0])[:2]
            if parents:
                parts.append("TOP PRIOR CANDIDATES (best first, with their "
                             "remaining failure evidence)\n" + "\n\n".join(
                                 f"--- {p[1]} score={p[0]:.0f} ---\nPROGRAM:\n{p[2]}\n"
                                 f"EVIDENCE:\n{p[3]}" for p in parents))
            if siblings:
                parts.append(
                    "THIS ROUND'S OTHER CANDIDATES (do NOT repeat their "
                    "strategy — explore a distinct one)\n"
                    + "\n\n".join(siblings))
            parts.append("Write the complete program."
                         if not parents else
                         "Write the complete program: either repair the best "
                         "candidate's specific failure, or take a distinct "
                         "strategy if the family looks stuck.")
            reply = chat.invoke([("system", SYNTH_SYSTEM),
                                 ("user", "\n\n".join(parts))])
            text = reply.content if isinstance(reply.content, str) else str(reply.content)
            program_source = _extract_program(text)
            if program_source is None:
                logger.error("%s: no ```python block; skipping candidate", label)
                continue
            program = programs_dir / f"attempt_{label}.py"
            program.write_text(program_source)

            run_dir = _run_episode(cli_args, program, logs_root)
            if run_dir is None:
                logger.error("%s: no run dir produced", label)
                continue
            episodes += 1
            if _terminated(run_dir):
                logger.info("%s: SOLVED (%s)", label, run_dir.name)
                (programs_dir / "solve.py").write_text(program_source)
                meta = {"suite": suite, "task": task, "debug_seed": debug_seed,
                        "rounds": round_no, "episodes": episodes, "k": k,
                        "run": run_dir.name, "source_attempt": program.name}
                (programs_dir / "solve.json").write_text(json.dumps(meta, indent=2))
                return {"solved": True, **meta}
            score = _score(run_dir)
            evidence = _attempt_digest(run_dir)
            logger.info("%s: failed, score=%.0f (%s)", label, score, run_dir.name)
            population.append((score, label, program_source, evidence))
            siblings.append(f"--- {label} score={score:.0f} ---\n{program_source}")

    return {"solved": False, "suite": suite, "task": task, "k": k,
            "rounds": max_attempts, "episodes": episodes,
            "best": max(population, key=lambda p: p[0])[1] if population else None}
