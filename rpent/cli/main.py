"""Physical agent main CLI entrypoint."""
# `rpent/cli/`
#
# CLI entrypoints for RPent (currently just `main.py`).
#
# ## Run
#
# `main()` is exposed as the `rpent` console script (see `[project.scripts]`
# in `pyproject.toml`):
#
# ```bash
# rpent --env libero --suite libero_object_task --task 0 --seed 0 [...]
# ```
#
# ## Note
#
# Do not import `rpent.cli` from other `rpent` modules. `main.py` pulls in
# `rpent.planner`, `rpent.envs`, `rpent.utils`, `rpent.dashboard`, and
# `rpent.tools`, so importing the CLI back into any of them would create an
# import cycle. Nothing else should depend on this package.
from __future__ import annotations

import argparse
import json
import queue
import shlex
import sys
import time
from collections.abc import Callable
from pathlib import Path

from rpent.cli.tui import (
    start_first_prompt_resolver,
    start_interactive_reader,
)
from rpent.dashboard.events import (
    NullDashboardEventSink,
    RunStartedEvent,
)
from rpent.envs import get_env_spec, get_toolkit
from rpent.planner.base import build_planner
from rpent.tools.sandbox import init_run_sandbox, memory_exposed
from rpent.utils.config import get_memory_common_dir, get_memory_env_dir
from rpent.utils.logging import get_logger, init_output_dir
from rpent.utils.resources import ensure_staged_priors

logger = get_logger("agent")

#: The experiment-episode task brief. It replaces the normal user message:
#: the goal is a CONTROLLED ANSWER ("which variant works"), not a solve —
#: the missing 0-to-1 discovery step for cells that have never succeeded.
#: A summariser can only learn "don't" from failures; contrast pairs from
#: deliberate trials are where "do" comes from.
_EXPERIMENT_BRIEF = """EXPERIMENT MODE — this episode is NOT scored and is NOT about completing the task.

Cell: suite={suite} task={task} seed={seed} (practice seed)
QUESTION TO SETTLE: {question}

Rules:
1. Controlled trials: change ONE variable per trial, hold everything else fixed.
2. Up to {trials} trials. Before each, state what you are changing and why;
   after each, record the outcome from tool evidence.
3. Record findings in RELATIVE terms that survive a re-randomised scene
   (offsets from measured features: rim centre, retreat direction, object
   top, graspable width) — never absolute coordinates.
4. End by writing {output_dir}/experiment_notes.md: one line per trial
   (what changed -> outcome), then THE WINNING RECIPE if any trial worked,
   in relative terms. Then call finish(status="experiment", summary=...).
5. NEVER end a message without a tool call — reasoning goes in text BEFORE
   a call. A message with no call halts the episode and loses your notes.
"""

#: The resident-debug-session task brief. Replaces the normal user message:
#: one continuous session debugs the SAME cell across multiple attempts
#: (reset_episode), keeping its own reasoning while archived tool results
#: fold to digests — the ASPIRE-shaped middle between an amnesiac
#: between-episode loop and an unbounded context.
_RESIDENT_BRIEF = """RESIDENT DEBUG SESSION — practice cell, multiple attempts allowed.

Cell: suite={suite} task={task} seed={seed} (practice seed)
GOAL: make this cell solve RELIABLY, then write the recipe down. This session
is done when the same recipe has solved the task TWICE (once, then reproduced
from a clean reset), or the turn budget is nearly spent.

Rules:
1. Work each attempt as one continuous episode: recover in place first.
   Reset only when the attempt is truly unrecoverable or the episode
   terminated — and diagnose BEFORE resetting: read the evidence, name the
   failure cause, and put both the cause and the planned change into
   reset_episode(reason=...). Never rerun a failed attempt unchanged.
2. After a reset, earlier attempts' tool results appear as one-line digests
   tagged [attempt N seq M]; your own reasoning stays. Drill into any digest
   with view_attempt_call(attempt=N, seq=M). Raw artifacts live in
   attempt_NN/ (read-only).
3. The seed re-creates the SAME initial layout, so treat archived readings
   as hypotheses — verify each with a fresh measurement in the current
   episode before committing a motion to it.
4. When the env terminates (libero_terminated=true), that attempt SOLVED:
   reset once more and reproduce the solve with the recipe as written. If
   the reproduction fails, the recipe is not done — keep debugging.
5. Before finishing, write {output_dir}/resident_notes.md:
   - per attempt, one line: what was tried -> outcome -> [attempt N seq M]
     citations for the decisive evidence;
   - then THE RECIPE in RELATIVE terms (offsets from measured features:
     rim centre, object top, graspable width — never absolute coordinates),
     step by step, with the evidence citation for each step.
   Then call finish(status="success" if the recipe reproduced else the
   honest status, summary=...).
6. NEVER end a message without a tool call — reasoning goes in text BEFORE
   a call. A message with no call halts the session and loses your notes.
"""


# ---------------------------------------------------------------------------
# API agent transcript serialization
# ---------------------------------------------------------------------------


def _strip_images(value):
    """Return a copy of ``value`` with inline image payloads omitted.

    SDK objects are left untouched; ``json.dump(..., default=str)`` handles
    them at write time. Only the bulky base64 image blocks are replaced.
    """
    if isinstance(value, list):
        return [_strip_images(v) for v in value]
    if isinstance(value, dict):
        if value.get("type") == "image":
            return {"type": "image", "source": {"_omitted_for_transcript": True}}
        if value.get("type") == "image_url":
            return {"type": "image_url", "image_url": {"_omitted_for_transcript": True}}
        return {k: _strip_images(v) for k, v in value.items()}
    return value


def _serialize_messages(messages: list[dict]) -> list[dict]:
    """Strip inline image payloads from messages before writing the transcript."""
    return [
        {**{k: v for k, v in m.items() if k != "content"},
         "content": _strip_images(m.get("content"))}
        for m in messages
    ]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Standalone hybrid LLM-in-the-loop agent for LIBERO PRO",
    )

    ap.add_argument("--env", dest="env_name", required=True, choices=["libero"],
                    help="Environment backend: libero.")

    # models
    ap.add_argument("--planner", default="api",
                    choices=["api", "deepagents", "claude_code", "codex"],
                    help="LLM backend: api | deepagents | claude_code | codex.")
    ap.add_argument("--model", default=None,
                    help="Model id. For the 'api' planner, prefix the provider "
                         "(e.g. anthropic:claude-opus-4-8, openai:gpt-5.5, "
                         "openai-chat:glm-5.2). For claude_code/codex this "
                         "overrides the backend default model.")
    ap.add_argument("--base-url", default=None,
                    help="API base URL. Defaults to the selected backend's base URL env var.")
    ap.add_argument("--max-turns", type=int, default=100)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--no-images", action="store_true",
                    help="Never send image bytes to the model (api planner only). "
                         "Use for text-only models that reject image input "
                         "(e.g. 400 \"message type 'image_url' is not supported\"); "
                         "read_image then returns the file path with a notice.")
    ap.add_argument("--planner-timeout-s", type=int, default=None,
                    help="Wall-clock cap for the claude_code/codex planner "
                         "subprocess. Defaults to CODEX_TIMEOUT_S (codex only), "
                         "CELL_TIMEOUT_S, or 1200.")
    ap.add_argument("--claude-code-max-budget-usd", type=float, default=None,
                    help="Budget passed to claude -p --max-budget-usd. "
                         "Defaults to MAX_BUDGET_USD env or 10.")

    # other config
    ap.add_argument("--sandbox", default="none",
                    help="Sandbox profile governing what the agent's file "
                         "tools may read and write: a name resolved in "
                         "configs/sandbox/ (none | memory | full | "
                         "unrestricted | any custom profile) or a path to a "
                         "profile .yaml. The sandbox is always on; the "
                         "resolved boundary is dumped to "
                         "{output_dir}/sandbox.json. Default: none (the "
                         "run's workspace only).")
    ap.add_argument("--experiment", default=None, metavar="QUESTION",
                    help="Run an EXPERIMENT episode instead of a task attempt: "
                         "the agent runs controlled trials to settle QUESTION "
                         "(one variable changed per trial, findings recorded in "
                         "relative terms) and writes experiment_notes.md. "
                         "Practice seeds (>=51) only — experiment episodes are "
                         "never scored. Pair with --sandbox practice.")
    ap.add_argument("--experiment-trials", type=int, default=5,
                    help="Max trials inside an experiment episode (default 5).")
    ap.add_argument("--vision-tool", default=None, metavar="MODEL_SPEC",
                    help="Arm the inspect_image channel: a vision model in "
                         "init_chat_model syntax (e.g. openai:glm-4.6v, "
                         "anthropic:claude-sonnet-4-6) that answers image "
                         "questions as a TOOL — the planner itself stays "
                         "text-only. Its replies pass through verbatim; "
                         "every call is recorded with the exact text sent. "
                         "deepagents planner only.")
    ap.add_argument("--vision-base-url", default=None,
                    help="Base URL for the --vision-tool model's API "
                         "(e.g. https://cloud.infini-ai.com/maas/v1).")
    ap.add_argument("--vision-max-tokens", type=int, default=1000,
                    help="Generation budget for one inspect_image reply "
                         "(a budget, never a post-hoc cut; default 1000).")
    ap.add_argument("--resident", action="store_true",
                    help="Resident debug session: one continuous session "
                         "debugs the SAME cell across multiple attempts. "
                         "Exposes reset_episode (archive to attempt_NN/ + env "
                         "reset) and view_attempt_call, and folds archived "
                         "attempts' tool results into seq-cited digests. "
                         "Practice seeds (>=51) and the deepagents planner "
                         "only. Pair with --sandbox practice and a raised "
                         "--max-turns.")
    ap.add_argument("--output-dir", default=None)
    ap.add_argument("--dashboard", action="store_true",
                    help="Start a local dashboard server for this single run.")
    ap.add_argument("--dashboard-host", default="127.0.0.1",
                    help="Dashboard bind host. Defaults to 127.0.0.1.")
    ap.add_argument("--dashboard-port", type=int, default=0,
                    help="Dashboard port. 0 asks the OS for a free port.")
    ap.add_argument("--dashboard-language", choices=["en", "zh-cn"], default="en",
                    help="Dashboard UI language. 'zh-cn' serves the Chinese "
                         "translation; defaults to English.")
    ap.add_argument("--verbose", action="store_true",
                    help="Enable DEBUG-level logging for stdout and the run.log "
                         "file. Defaults to INFO when not set.")
    ap.add_argument("--interactive", "-i", action="store_true",
                    help="Interactive mode: opens an interactive cli session.")

    return ap


def main() -> int:
    parser = _build_argparser()
    # Two-phase argparse: first grab --env / --dashboard so we know which
    # env's flags to add and whether to make its required flags optional.
    early, _ = parser.parse_known_args()

    env_spec = get_env_spec(early.env_name)
    env_spec.add_cli_args(parser, use_dashboard=early.dashboard)
    args = parser.parse_args()
    if args.dashboard and args.interactive:
        parser.error("--dashboard and --interactive cannot be used together")
    if args.dashboard:
        from rpent.cli.dashboard import run_dashboard_session

        return run_dashboard_session(args, env_spec, parser=parser)

    run_config = env_spec.parse_config(args)
    recipe_tag = run_config.recipe_tag
    output_dir = run_config.output_dir
    prompt_vars = run_config.prompt_vars
    task_desc = run_config.task_desc

    env_name = args.env_name

    if args.vision_tool:
        if args.planner != "deepagents":
            parser.error("--vision-tool requires --planner deepagents")
        from rpent.tools import vision

        vision.configure(args.vision_tool, base_url=args.vision_base_url,
                         max_tokens=args.vision_max_tokens)
        logger.info("vision channel armed: %s (base_url=%s)",
                    args.vision_tool, args.vision_base_url or "provider default")

    if args.resident:
        # The resident surface (reset_episode, folding) exists only on the
        # deepagents planner, and a reset on a scoring seed would turn an
        # exam into practice — both are refused here, not discouraged.
        if args.planner != "deepagents":
            parser.error("--resident requires --planner deepagents")
        if args.experiment:
            parser.error("--resident and --experiment are different session "
                         "kinds; pick one")
        try:
            seed_num = int(prompt_vars.get("seed"))
        except (TypeError, ValueError):
            seed_num = None
        if seed_num is not None and seed_num < 51:
            parser.error(
                f"--resident runs on practice seeds (>=51); seed {seed_num} "
                "is a scoring seed and a multi-attempt session there would "
                "poison it"
            )

    # mkdir + logging wiring (env-side already picked the path).
    output_dir = init_output_dir(output_dir, verbose=args.verbose)
    logger.info("physical agent cmd: %s", shlex.join([sys.executable, *sys.argv]))

    sandbox_policy = init_run_sandbox(
        args.sandbox, env_name, output_dir,
        extra_bindings={k: prompt_vars.get(k) for k in ("suite", "task")},
    )
    logger.info(
        "sandbox profile '%s': read %s",
        sandbox_policy.name,
        [str(p) for p in sandbox_policy.read_roots],
    )
    ensure_staged_priors(env_name, enabled=sandbox_policy.uses_staging)

    dashboard_events = NullDashboardEventSink()

    planner = build_planner(
        args.planner,
        output_dir=output_dir,
        recipe_tag=recipe_tag,
        env_name=env_name,
        base_url=args.base_url,
        model=args.model,
        max_tokens=args.max_tokens,
        planner_timeout_s=args.planner_timeout_s,
        claude_code_max_budget_usd=args.claude_code_max_budget_usd,
        dashboard_events=dashboard_events,
        no_images=args.no_images,
        resident=args.resident,
        vision=bool(args.vision_tool),
    )
    prompt_bundle = env_spec.prompts
    prompt_vars = {
        **prompt_vars,
        "output_dir": output_dir,
        "memory_common": get_memory_common_dir(),
        "memory_env": get_memory_env_dir(env_name),
    }
    # The prompt varies with the sandbox's CAPABILITIES, not its name: the
    # library step exists iff the library is actually readable this run, and
    # the playbook line iff this task's playbook root is readable.
    memory_on = memory_exposed(env_name)
    playbook_on = False
    if sandbox_policy is not None and prompt_vars.get("suite") is not None \
            and prompt_vars.get("task") is not None:
        from rpent.utils.config import get_repo_root

        task_dir = (get_repo_root() / "memory" / "tasks"
                    / str(prompt_vars["suite"]) / f"t{prompt_vars['task']}")
        # Readable AND existing: advertising an empty root cost the agent a
        # confused list_dir on the first playbook-less practice run.
        playbook_on = sandbox_policy.can_read(task_dir) and task_dir.is_dir()
        if playbook_on:
            prompt_vars["memory_task"] = task_dir
    system_prompt = prompt_bundle.render(
        "system",
        variables=prompt_vars,
        memory=memory_on,
        playbook=playbook_on,
        resident=args.resident,
    )
    user_msg = prompt_bundle.render(
        "user",
        variables=prompt_vars,
        memory=memory_on,
        playbook=playbook_on,
        resident=args.resident,
    )
    if args.resident:
        user_msg = _RESIDENT_BRIEF.format(
            suite=prompt_vars.get("suite", "?"),
            task=prompt_vars.get("task", "?"),
            seed=prompt_vars.get("seed", "?"),
            output_dir=output_dir,
        )
        logger.info("RESIDENT debug session on practice seed %s",
                    prompt_vars.get("seed"))
    if args.experiment:
        try:
            seed_num = int(prompt_vars.get("seed"))
        except (TypeError, ValueError):
            seed_num = None
        if seed_num is not None and seed_num < 51:
            parser.error(
                f"--experiment runs on practice seeds (>=51); seed {seed_num} "
                "is a scoring seed and an experiment there would poison it"
            )
        user_msg = _EXPERIMENT_BRIEF.format(
            suite=prompt_vars.get("suite", "?"),
            task=prompt_vars.get("task", "?"),
            seed=prompt_vars.get("seed", "?"),
            question=args.experiment,
            trials=args.experiment_trials,
            output_dir=output_dir,
        )
        logger.info("EXPERIMENT episode: %s", args.experiment)

    input_queue: "queue.Queue[str | None] | None" = None
    await_first_prompt: "Callable[[], str | None] | None" = None
    if args.interactive:
        input_queue = queue.Queue()
        # Pre-fill the first prompt with the rendered default task (editable
        # preset);
        start_interactive_reader(input_queue, first_prompt_default=user_msg)
        logger.info(
            "interactive mode on: the built-in task is pre-filled — "
            "edit it and press Enter, submit it as-is, or clear it to "
            "type your own. Once running, type to steer the agent. "
            "/help for commands."
        )
        # Resolve the opening prompt on a background thread so the user can type
        # it while the (slow) env/VLA servers boot below.
        await_first_prompt = start_first_prompt_resolver(input_queue)

    # --- initialise environment --------------------------------------------
    daemons, primitives_kwargs = env_spec.init_runtime(
        args,
        output_dir,
        dashboard_events,
    )

    # --- toolkit -----------------------------------------------------------
    toolkit = get_toolkit(
        env_name,
        primitives_kwargs=primitives_kwargs,
        video_path=str(Path(output_dir) / "episode.mp4"),
        dashboard_events=dashboard_events,
    )

    # --- agent loop --------------------------------------------------------
    t0 = time.time()
    finish_result, messages, agent_error = None, [], None
    stats: dict = {}
    first_user_msg: str | None = user_msg
    if await_first_prompt is not None:
        # Block until the opening prompt typed during startup is ready.
        first_user_msg = await_first_prompt()
        if first_user_msg is None:
            logger.info("no task entered; ending session before start.")
    try:
        if first_user_msg is not None:
            dashboard_events.emit(RunStartedEvent())
            result = planner.solve(
                system_prompt=system_prompt,
                user_message=first_user_msg,
                toolkit=toolkit,
                max_turns=args.max_turns,
                input_queue=input_queue,
            )
            finish_result = result.finish_result
            messages = result.messages
            stats = result.stats
            agent_error = result.error
    except Exception as exc:
        logger.error("EXCEPTION in agent loop: %s", exc)
        agent_error = str(exc)
    finally:
        # Agent-side: flush the episode video before the env+model
        recipe_path = toolkit.write_recipe(recipe_tag)
        logger.info("recipe: %s", recipe_path)

        toolkit.close()
        for d in daemons:
            d.stop()

    elapsed = time.time() - t0

    transcript_path = Path(output_dir) / f"transcript_{recipe_tag}.json"
    record = {
        **task_desc,
        "model": args.model,
        "elapsed_s": round(elapsed, 1),
        "finish": finish_result,
        "stats": stats,
        "messages": _serialize_messages(messages),
    }
    with open(transcript_path, "a") as f:
        json.dump(record, f, indent=2, default=str)

    logger.info("elapsed: %.1fs", elapsed)
    logger.info("usage: in=%s out=%s tool_calls=%s",
                 stats.get('total_input_tokens', '?'),
                 stats.get('total_output_tokens', '?'),
                 stats.get('tool_calls', '?'))
    logger.info("transcript: %s", transcript_path)
    if agent_error:
        logger.error("error: %s", agent_error)

    return 0


if __name__ == "__main__":
    sys.exit(main())
