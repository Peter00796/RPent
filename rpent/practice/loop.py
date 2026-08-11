"""Orchestrate practice rounds for one cell until it cracks.

LLM usage is confined to two places, both out-of-episode: the existing
observer (mining a failed run) and the playbook updater below (turning
observations into task-scoped proposals plus, optionally, ONE open question
for a targeted experiment). Everything else is the same machinery every
other run uses — episodes are real ``rpent.cli.main`` subprocesses, and
admissions go through the same gate checks with auto-admit ONLY for
mechanically clean proposals (anything flagged is skipped and logged; a
human can revisit the round directory later).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

from rpent.gate import tokens
from rpent.gate.apply import _apply_one  # the library's single writer
from rpent.gate.checks import run_checks
from rpent.gate.observe import observe_run, split_blocks
from rpent.gate.proposal import load_proposal
from rpent.utils.config import get_repo_root
from rpent.utils.logging import get_logger

logger = get_logger("practice")

UPDATE_SYSTEM = """You are the playbook updater for ONE robot-manipulation task
cell. You receive: the task ref, the CURRENT playbook (may be empty), and
cited observations from the latest failed practice episode(s).

Produce:
1. Zero or more PROPOSALS that would have prevented the observed failure —
   task-scoped knowledge only (object identities, working phrasings, winning
   step recipes for THIS cell). Rules, all hard:
   - evidence cites run records (run:<run_dir>#seq=N), copied exactly from
     the observations; a claim you cannot cite, you do not write.
   - RELATIVE terms only (offsets from measured features); absolute
     coordinates die with the seed and will be rejected.
   - Do not restate what the current playbook already says; refine it via
     action: revise (target: the entry path, copied VERBATIM) or add what is
     missing. Fewer, sharper entries beat many vague ones.
2. If the failure looks like something no summary can settle — two variants
   must be TRIED to know which works — output exactly one OPEN QUESTION for a
   controlled experiment episode: a single-focus question, one variable per
   trial, phrased for the experimenter.

Format, nothing else:

===PROPOSAL===
---
title: <imperative>
action: add | revise
type: technique | invariant | failure_mode
scope: task
task: {task_ref}
target: <existing entry path, revise only>
conditions: <when it applies>
evidence:
  - cite: run:<run_dir_name>#seq=<n>
    role: <what it shows>
counter_evidence: []
---
<body>

===OPEN QUESTION===
<one question, or omit this block entirely>
"""


def _sh(cli_args: list[str], log_path: Path, timeout_s: int = 1500) -> int:
    cmd = [sys.executable, "-m", "rpent.cli.main", *cli_args]
    with open(log_path, "w") as log:
        try:
            proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
                                  timeout=timeout_s)
            return proc.returncode
        except subprocess.TimeoutExpired:
            return -9


def _newest_run(logs_root: Path, suite: str, task: int, seed: int) -> Path | None:
    runs = sorted(logs_root.glob(f"*_{suite}_t{task}_s{seed}"),
                  key=lambda p: p.stat().st_mtime)
    return runs[-1] if runs else None


def _terminated(run_dir: Path) -> bool:
    try:
        states = json.loads((run_dir / "states.json").read_text())
    except Exception:
        return False
    return any(e.get("libero_terminated")
               or (e.get("result") or {}).get("libero_terminated")
               for e in states if isinstance(e, dict))


def _playbook_dir(suite: str, task: int) -> Path:
    return get_repo_root() / "memory" / "tasks" / suite / f"t{task}"


def _playbook_text(suite: str, task: int) -> str:
    directory = _playbook_dir(suite, task)
    if not directory.is_dir():
        return "(the playbook is empty)"
    chunks = []
    for path in sorted(directory.glob("*.md")):
        chunks.append(f"### memory/tasks/{suite}/t{task}/{path.name}\n"
                      + path.read_text())
    return "\n\n".join(chunks) or "(the playbook is empty)"


def _observations_text(run_dir: Path) -> str:
    chunks = [p.read_text() for p in sorted(run_dir.glob("observations/*.md"))]
    return "\n\n".join(chunks) or "(no observations)"


def update_playbook(*, suite: str, task: int, failed_runs: list[Path],
                    round_dir: Path, model: str, base_url: str | None,
                    memory_root: Path) -> dict:
    """Mine failures into auto-admitted playbook entries + an open question."""
    from langchain.chat_models import init_chat_model

    task_ref = f"{suite}/t{task}"
    observations = "\n\n".join(
        f"--- from {r.name} ---\n{_observations_text(r)}" for r in failed_runs)
    payload = (f"TASK: {task_ref}\n\nCURRENT PLAYBOOK\n"
               f"{_playbook_text(suite, task)}\n\nOBSERVATIONS\n{observations}")
    chat = init_chat_model(model, **({"base_url": base_url} if base_url else {}))
    reply = chat.invoke([("system", UPDATE_SYSTEM.replace("{task_ref}", task_ref)),
                         ("user", payload)])
    text = reply.content if isinstance(reply.content, str) else str(reply.content)

    question = None
    if "===OPEN QUESTION===" in text:
        text, tail = text.split("===OPEN QUESTION===", 1)
        question = tail.strip().split("===")[0].strip() or None

    proposals_dir = round_dir / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    admitted, skipped = [], []
    runs = tokens.run_map(failed_runs)
    batch = round_dir.name
    for i, block in enumerate(split_blocks(text, "===PROPOSAL==="), 1):
        path = proposals_dir / f"proposal_{i:02d}.md"
        path.write_text(block + "\n")
        p = load_proposal(path)
        review = run_checks(p, runs, memory_root, "libero", [])
        (round_dir / f"review_{i:02d}.json").write_text(json.dumps(
            {"suggested": review.suggested, "destination": review.destination,
             "findings": [f"[{f.check}/{f.level}] {f.message}"
                          for f in review.findings]}, indent=2))
        if review.suggested == "admit":
            outcome = _apply_one(p, review.destination, memory_root, batch)
            admitted.append(outcome)
            logger.info("playbook: %s", outcome)
        else:
            skipped.append(f"{path.name}: {review.suggested}")
            logger.info("playbook: skipped %s (%s)", path.name, review.suggested)
    return {"admitted": admitted, "skipped": skipped, "question": question}


def practice_loop(*, suite: str, task: int, practice_seeds: list[int],
                  exam_seed: int, max_rounds: int, model: str,
                  base_url: str | None, logs_root: Path,
                  max_exams: int = 2) -> dict:
    """Rounds of attempt → mine → update until the exam passes."""
    repo = get_repo_root()
    memory_root = repo / "memory"
    root = logs_root / f"practice_{suite}_t{task}"
    root.mkdir(parents=True, exist_ok=True)
    history: list[dict] = []
    pending_question: str | None = None
    exams_taken = 0

    def episode(seed: int, experiment: str | None, tag: str) -> Path | None:
        args = ["--env", "libero", "--suite", suite, "--task", str(task),
                "--seed", str(seed), "--sandbox", "practice",
                "--planner", "deepagents", "--model", model, "--no-images",
                "--max-turns", "50" if experiment is None else "35"]
        if base_url:
            args += ["--base-url", base_url]
        if experiment is not None:
            args += ["--experiment", experiment]
        rc = _sh(args, root / f"{tag}.out")
        run = _newest_run(logs_root, suite, task, seed)
        logger.info("%s: rc=%s run=%s", tag, rc, run.name if run else None)
        return run

    for round_no in range(1, max_rounds + 1):
        round_dir = root / f"round_{round_no:02d}"
        round_dir.mkdir(exist_ok=True)
        entry: dict = {"round": round_no}

        if pending_question:
            # Knowledge stalled last round; probe the miner's own question.
            entry["experiment"] = pending_question
            run = episode(practice_seeds[0], pending_question,
                          f"round{round_no:02d}_experiment")
            pending_question = None
            failed = [run] if run else []
            solved_all = False
        else:
            failed, solved_all = [], True
            for seed in practice_seeds:
                run = episode(seed, None, f"round{round_no:02d}_s{seed}")
                if run is None:
                    solved_all = False
                    continue
                if _terminated(run):
                    logger.info("round %d: practice seed %d SOLVED", round_no, seed)
                else:
                    solved_all = False
                    failed.append(run)

        if solved_all and exams_taken < max_exams:
            exams_taken += 1
            entry["exam"] = exams_taken
            run = episode(exam_seed, None, f"round{round_no:02d}_exam")
            if run is not None and _terminated(run):
                entry["result"] = "EXAM SOLVED"
                history.append(entry)
                (root / "history.json").write_text(json.dumps(history, indent=2))
                return {"solved": True, "rounds": round_no,
                        "exams_taken": exams_taken, "run": run.name,
                        "history": history}
            entry["result"] = "exam failed"
            if run is not None:
                failed.append(run)

        if failed:
            for run in failed:
                if not (run / "observations").is_dir():
                    observe_run(run, model, base_url)
            update = update_playbook(
                suite=suite, task=task, failed_runs=failed,
                round_dir=round_dir, model=model, base_url=base_url,
                memory_root=memory_root)
            entry.update({k: update[k] for k in ("admitted", "skipped")})
            if not update["admitted"]:
                pending_question = update["question"]
                entry["next"] = ("experiment: " + pending_question[:80]
                                 if pending_question else "no new knowledge")
        history.append(entry)
        (root / "history.json").write_text(json.dumps(history, indent=2))

    return {"solved": False, "rounds": max_rounds, "exams_taken": exams_taken,
            "history": history}
