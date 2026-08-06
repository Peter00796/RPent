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

import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rpent.tools.toolkit import ToolCancelled
from rpent.utils.logging import get_logger

from robots.libero.tools import databus
from robots.libero.tools.artifacts import ARTIFACT_DIRECTORIES, artifact_path
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
