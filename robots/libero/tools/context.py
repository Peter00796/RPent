"""Per-run context the LIBERO agent tools receive through ``ToolRuntime``.

The tools are module-level functions, so the live env/policy handles reach them
through the graph's context object rather than a closure or a global — one
instance per run, which keeps parallel runs isolated.

:meth:`LiberoContext.advance` is the one place the per-action bookkeeping lives:
timing, the action video slice, the ``states.json`` dump, and rendering the new
state back to the planner. It replaces ``LiberoToolkit._step``, and it is what a
future middleware stack should absorb — each of its responsibilities is a
cross-cutting concern, not tool logic.
"""
from __future__ import annotations

import json
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rpent.tools import sandbox, tool_log
from rpent.tools.toolkit import ToolCancelled
from rpent.utils.logging import get_logger

from robots.libero.tools import databus
from robots.libero.tools.artifacts import (
    ARTIFACT_DIRECTORIES,
    artifact_path,
    protected_paths,
)
from robots.libero.tools.primitives import LiberoPrimitives
from robots.libero.tools.state import dump_state, view_driver_state

logger = get_logger("libero_context")


def _no_op() -> None:
    """Default cancellation check: never cancels."""


@dataclass
class LiberoContext:
    """Everything a LIBERO tool call needs beyond its own arguments.

    Attributes:
        primitives: The live env + policy + SAM3 handle.
        output_dir: Run artifact root. Every path is resolved under it.
        check_cancelled: Raises :class:`ToolCancelled` at a safe boundary.
        record_action_videos: Write ``action_videos/step_NN_<tool>.mp4`` per
            action. Previously keyed off whether the dashboard was enabled,
            which made a run's artifacts depend on the UI; it is now explicit.
        video_fps: Frame rate for those clips.
        on_step: Optional hook called with each rendered state view, for
            dashboard/telemetry projection. Kept as a callback so the tool layer
            has no dependency on any UI.
    """

    primitives: LiberoPrimitives
    output_dir: Path
    check_cancelled: Callable[[], None] = _no_op
    record_action_videos: bool = False
    video_fps: int = 20
    on_step: Callable[[dict[str, Any]], None] | None = None
    step_idx: int = field(default=0, init=False)
    #: 1-based attempt counter for resident debug sessions. Stays at 1 for
    #: exam runs, where ``reset_episode`` does not exist.
    attempt_no: int = field(default=1, init=False)

    # ------------------------------------------------------------------
    # Episode lifecycle
    # ------------------------------------------------------------------

    def begin_episode(self) -> dict[str, Any]:
        """Wipe stale artifacts, reset the env, and dump step 0."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        for sub in ARTIFACT_DIRECTORIES:
            target = self.output_dir / sub
            if target.exists():
                shutil.rmtree(target)
        for target in (
            artifact_path(self.output_dir, "states"),
            artifact_path(
                self.output_dir, "metadata", camera="agentview", resolution="low"
            ),
            artifact_path(self.output_dir, "episode_video"),
            # Both are per-run, append-only records. Left behind, a re-run in the
            # same output directory appends to the previous episode's log with the
            # sequence restarted, which makes the file unreadable as a single run.
            artifact_path(self.output_dir, "entities"),
            tool_log.path_for(self.output_dir),
        ):
            if target.exists():
                target.unlink()

        self.primitives.reset()
        self.primitives.start_recording()
        self.step_idx = 0
        dump_state(self.primitives, str(self.output_dir), step_idx=0, log=None)
        view = view_driver_state(0)
        if self.on_step is not None:
            self.on_step(view)
        return view

    def reset_episode(self, reason: str) -> dict[str, Any]:
        """Archive the running episode into ``attempt_NN/`` and start fresh.

        Resident debug sessions only — the tool that calls this is not on the
        exam surface. v1 rotation is a plain rename: the archived attempt is
        complete on disk (states, tool-call log, images, world maps, its own
        episode video) but replay/gate tooling reads the live layout, so they
        see only the newest attempt until taught otherwise (accepted 08-11).

        The archive is registered write-protected: evidence of a failed
        attempt must survive the session that produced it.
        """
        attempt_dir = self.output_dir / f"attempt_{self.attempt_no:02d}"
        if attempt_dir.exists():
            return {
                "error": f"{attempt_dir.name} already exists — the rotation "
                         "state is inconsistent; do not reset again",
            }
        attempt_dir.mkdir(parents=True)

        # Flush the in-memory frame buffer as the attempt's own episode video
        # before begin_episode() restarts the recording (which clears it).
        try:
            self.primitives.stop_recording_and_save(
                str(attempt_dir / "episode.mp4"), fps=self.video_fps
            )
        except Exception as e:
            logger.warning("attempt %d: episode video not saved: %s",
                           self.attempt_no, e)

        # Everything the artifact layout owns, plus the tool-call log.
        for path in (*protected_paths(self.output_dir),
                     tool_log.path_for(self.output_dir)):
            if path.exists():
                path.rename(attempt_dir / path.name)

        (attempt_dir / "attempt.json").write_text(json.dumps({
            "attempt": self.attempt_no,
            "reason": reason,
            "env_steps": self.step_idx,
        }, indent=2))
        sandbox.add_write_protection([attempt_dir])

        archived = self.attempt_no
        self.attempt_no += 1
        # Per-attempt seq numbering: each attempt's log restarts at 1, so a
        # ``[attempt N seq M]`` citation is unambiguous. The reset call itself
        # is recorded by the log middleware AFTER this returns, landing as
        # seq 1 of the new attempt's log.
        tool_log.reset_sequence()
        view = self.begin_episode()
        return {
            "attempt": self.attempt_no,
            "archived_to": attempt_dir.name,
            "note": (
                "fresh episode on the same cell and seed. Every entity "
                "registration died with the old episode — re-localize before "
                "any motion. Archived tool results appear as one-line "
                "digests; retrieve one in full with view_attempt_call."
            ),
            **view,
        }

    # ------------------------------------------------------------------
    # One env-advancing action
    # ------------------------------------------------------------------

    def advance(
        self,
        name: str,
        args: dict[str, Any],
        primitive: Callable[..., Any],
    ) -> dict[str, Any]:
        """Run one environment-advancing primitive and dump the resulting step.

        Args:
            name: Tool name, used for the command log and the video filename.
            args: The primitive's keyword arguments, logged verbatim as the
                command so the recipe export can replay them.
            primitive: The bound primitive method to call with ``**args``.

        Returns:
            The rendered state view for the newly dumped step, with
            ``agent_elapsed_s`` added. If the call was interrupted, the
            cancellation fields are merged in.
        """
        # A finished episode cannot step again — the env client asserts on it
        # (a protocol invariant we keep). Surface it as information instead
        # of a crash: experiment episodes in particular keep probing after an
        # accidental solve or a truncation, and one late motion call must not
        # cost the run its notes.
        env = getattr(self.primitives, "env", None)
        if env is not None and (getattr(env, "episode_terminated", False)
                                or getattr(env, "episode_truncated", False)):
            return {
                "error": "the episode already signaled termination/truncation "
                         "— no further env steps are possible. Save your "
                         "notes/audit with write_text_file and call finish().",
                "libero_terminated": bool(getattr(env, "episode_terminated", False)),
            }
        command = {"action": name, **args}
        t0 = time.time()
        start_frame = self.primitives.recorded_frame_count()
        eef_before = self.primitives._last_obs_eef_pos
        try:
            result = primitive(**args)
            self.check_cancelled()
        except ToolCancelled as exc:
            result = {
                "error": str(exc),
                "code": "tool_cancelled",
                "interrupted": True,
            }
        elapsed = round(time.time() - t0, 2)

        result_dict = result if isinstance(result, dict) else {"value": result}

        self.step_idx += 1
        step_idx = self.step_idx
        if self.record_action_videos:
            video_path = (
                artifact_path(self.output_dir, "action_videos")
                / f"step_{step_idx:02d}_{name}.mp4"
            )
            try:
                self.primitives.save_frame_slice(
                    start_frame, str(video_path), fps=self.video_fps
                )
            except Exception as e:
                logger.warning("failed to save action clip to %s: %s", video_path, e)

        # The world just changed, so every registered reading loses its
        # freshness. The harness decides how much: proximity to where the
        # end-effector went separates "possibly bumped" from merely "no longer
        # verified". Interpreting that is the planner's job, not ours.
        if eef_before is not None:
            databus.mark_after_motion(
                self.output_dir,
                eef_before=eef_before,
                eef_after=self.primitives._last_obs_eef_pos,
                gripper_open=(self.primitives._last_obs_gripper or 0.0) > 0.06,
            )

        dump_state(
            self.primitives,
            str(self.output_dir),
            step_idx=step_idx,
            log={"command": command, "result": result_dict, "elapsed_s": elapsed},
        )
        view = view_driver_state(step_idx)
        view["agent_elapsed_s"] = elapsed
        if result_dict.get("interrupted"):
            view.update(result_dict)
        if self.on_step is not None:
            self.on_step(view)
        return view
