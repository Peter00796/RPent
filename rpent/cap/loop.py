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


def cap_loop(*, suite: str, task: int, debug_seed: int, model: str,
             base_url: str | None, max_attempts: int, logs_root: Path,
             extra_cli: list[str]) -> dict:
    """Write/run/debug until the debug seed passes or attempts run out."""
    from langchain.chat_models import init_chat_model

    programs_dir = get_repo_root() / "programs" / suite / f"t{task}"
    programs_dir.mkdir(parents=True, exist_ok=True)
    chat = init_chat_model(model, **({"base_url": base_url} if base_url else {}))
    api_doc = render_api_doc()
    memory = _memory_digest()

    task_line = (f"suite={suite} task={task} seed={debug_seed} — write a program "
                 "that solves this cell's manipulation task.")
    history: list[str] = []
    cli_args = ["--env", "libero", "--suite", suite, "--task", str(task),
                "--seed", str(debug_seed), "--sandbox", "none", *extra_cli]

    for attempt in range(1, max_attempts + 1):
        parts = [f"TASK\n{task_line}", f"API\n{api_doc}",
                 f"TECHNIQUE LIBRARY\n{memory}"]
        if history:
            parts.append("PRIOR ATTEMPTS (oldest first)\n" + "\n\n".join(history))
            parts.append("Revise the program. Output the complete program.")
        else:
            parts.append("Write the first version. Output the complete program.")
        reply = chat.invoke([("system", SYNTH_SYSTEM), ("user", "\n\n".join(parts))])
        text = reply.content if isinstance(reply.content, str) else str(reply.content)
        program_source = _extract_program(text)
        if program_source is None:
            logger.error("attempt %d: no ```python block in the reply; retrying", attempt)
            history.append(f"--- attempt {attempt}: reply had no python block ---")
            continue
        program = programs_dir / f"attempt_{attempt:02d}.py"
        program.write_text(program_source)

        run_dir = _run_episode(cli_args, program, logs_root)
        if run_dir is None:
            logger.error("attempt %d: no run dir produced", attempt)
            break
        solved = _terminated(run_dir)
        logger.info("attempt %d: %s (%s)", attempt,
                    "SOLVED" if solved else "failed", run_dir.name)
        if solved:
            frozen = programs_dir / "solve.py"
            frozen.write_text(program_source)
            meta = {"suite": suite, "task": task, "debug_seed": debug_seed,
                    "attempts": attempt, "run": run_dir.name,
                    "source_attempt": program.name}
            (programs_dir / "solve.json").write_text(json.dumps(meta, indent=2))
            return {"solved": True, **meta}
        history.append(
            f"--- attempt {attempt} (FAILED) ---\nPROGRAM:\n{program_source}\n"
            f"EVIDENCE:\n{_attempt_digest(run_dir)}"
        )

    return {"solved": False, "suite": suite, "task": task,
            "attempts": max_attempts}
