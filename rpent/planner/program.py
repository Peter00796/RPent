"""The program-executor planner: a run driven by a FIXED Python program.

Zero LLM calls inside the episode — this is the in-loop half of the
code-as-policy arm (see :mod:`rpent.cap`). The program file defines::

    def solve(api):
        ...  # calls api["segment"](...), api["move_to"](...), api["finish"](...)

or, equivalently, top-level code using the same names as globals. Execution
ends when the program calls ``finish(status, summary)``, returns, raises, or
the env terminates mid-primitive. Whatever happens, the episode's evidence
is complete: every API call went through the same handlers as the tool
planners, so ``tool_calls.jsonl`` / states / replay / sandbox behave
identically — the two policy forms differ only in who decides the next call.

The traceback of a failed program is part of the run's evidence
(``analysis/program_error.txt``): the out-of-loop coding agent debugs from
the recorded episode, not from a live debugger.
"""
from __future__ import annotations

import hashlib
import json
import queue
import traceback
from pathlib import Path

from rpent.dashboard.events import DashboardEventSink
from rpent.dashboard.interaction import DashboardInteractionPort
from rpent.planner.base import PlannerResult
from rpent.tools.toolkit import Toolkit
from rpent.utils.logging import get_logger

logger = get_logger("program_planner")


class ProgramPlanner:
    """Execute one program file against the toolkit's context."""

    def __init__(self, *, program_file: str, output_dir: str | Path,
                 dashboard_events: DashboardEventSink) -> None:
        self._program_file = Path(program_file)
        self._output_dir = Path(output_dir)
        self._dashboard_events = dashboard_events

    def solve(
        self,
        *,
        system_prompt: str,
        user_message: str,
        toolkit: Toolkit,
        max_turns: int,
        input_queue: "queue.Queue[str | None] | None" = None,
        dashboard_interaction: DashboardInteractionPort | None = None,
    ) -> PlannerResult:
        from rpent.cap.api import ProgramHalt, exec_namespace, make_api

        if input_queue is not None or dashboard_interaction is not None:
            raise NotImplementedError(
                "the program planner runs a fixed program; there is nothing "
                "to steer interactively"
            )
        source = self._program_file.read_text()
        program_sha = hashlib.sha256(source.encode()).hexdigest()
        # The program is this run's policy: record exactly which one ran.
        (self._output_dir / "program.json").write_text(json.dumps({
            "file": str(self._program_file),
            "sha256": program_sha,
        }, indent=2))
        (self._output_dir / "program.py").write_text(source)
        logger.info("executing program %s (sha256 %s)",
                    self._program_file, program_sha[:12])

        ctx = toolkit.tool_context
        namespace = exec_namespace(make_api(ctx, output_dir=self._output_dir))

        finish_result = None
        error = None
        try:
            code = compile(source, str(self._program_file), "exec")
            exec(code, namespace)  # noqa: S102 — the restricted namespace IS the sandbox
            solve = namespace.get("solve")
            if callable(solve):
                solve(dict(namespace))
            # Program ended without calling finish: report that honestly.
            finish_result = {"_finish": True, "status": "ended",
                             "summary": "program returned without calling finish"}
        except ProgramHalt as halt:
            finish_result = halt.result
        except Exception:
            tb = traceback.format_exc()
            error = tb.strip().splitlines()[-1]
            analysis = self._output_dir / "analysis"
            analysis.mkdir(parents=True, exist_ok=True)
            (analysis / "program_error.txt").write_text(tb)
            logger.error("program raised; traceback saved to analysis/program_error.txt")
            finish_result = {"_finish": True, "status": "error", "summary": error}

        step_idx = getattr(ctx, "step_idx", None)
        return PlannerResult(
            finish_result=finish_result,
            messages=[{"role": "program", "content": f"{self._program_file.name} "
                       f"sha256={program_sha[:12]}"}],
            stats={"turns_used": 0, "tool_calls": 0, "total_input_tokens": 0,
                   "total_output_tokens": 0, "env_steps": step_idx,
                   "program_sha256": program_sha},
            error=error,
        )
