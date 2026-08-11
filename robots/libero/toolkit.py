"""LIBERO toolkit: common tools + LIBERO primitives.

Inherits the common file/IO tools from :class:`Toolkit` and registers the
LIBERO primitives (``move_to``, ``pi0_pick``, ``release``, ...) on top.
"""
from __future__ import annotations

import shutil
import time
from functools import partial
from typing import Any

from robots.libero import tools as libero_tools
from robots.libero.tools import perception as libero_perception
from robots.libero.tools import state as libero_state
from rpent.dashboard.events import DashboardEventSink, ToolResultEvent
from rpent.tools import sandbox, tool_log
from rpent.tools.toolkit import ToolCancelled, Toolkit
from rpent.utils.logging import get_logger, get_output_dir


class LiberoToolkit(Toolkit):
    """Toolkit for the LIBERO environment."""

    # Tool schemas keyed by name. Derived from the native LangChain tools via
    # the legacy shim, so this pre-LangChain path shows the model exactly the
    # same schemas as the LangChain planner does.
    _SPECS = {spec["name"]: spec for spec in libero_tools.legacy_tool_specs()}

    def __init__(
        self,
        *,
        primitives_kwargs: dict[str, Any],
        dashboard_events: DashboardEventSink,
        video_path: str | None = None,
    ) -> None:
        super().__init__(dashboard_events=dashboard_events)
        self._next_step: int = 0
        self._video_path: str | None = video_path
        self.init_primitives_clean(primitives_kwargs=primitives_kwargs)
        self._register_libero_tools()
        # Context for the native LangChain tools. It wraps the primitives this
        # toolkit already built and reset, so it starts at step 0 and must not
        # call begin_episode() — init_primitives_clean did that work.
        self.tool_context = libero_tools.LiberoContext(
            primitives=self._primitives,
            output_dir=get_output_dir(),
            check_cancelled=self.raise_if_cancelled,
            record_action_videos=dashboard_events.enabled,
            on_step=self._emit_step_view,
        )
        # The run's evidence is read-only to the agent: everything the
        # artifact layout owns, the tool-call log, and the run log itself.
        _out = get_output_dir()
        sandbox.add_write_protection([
            *libero_tools.artifacts.protected_paths(_out),
            tool_log.path_for(_out),
            _out / "run.log",
            _out / "sandbox.json",
        ])

    def _emit_step_view(self, view: dict[str, Any]) -> None:
        """Project one rendered state view to the Dashboard."""
        self._dashboard_events.emit(
            ToolResultEvent(name="view_driver_state", result=view)
        )

    def langchain_tools(self, *, no_images: bool = False,
                        resident: bool = False) -> list[Any]:
        """Common tools plus the LIBERO tools, as native LangChain tools.

        ``resident=True`` appends ``reset_episode`` — the tool exists only in
        resident practice sessions, so an exam run cannot be talked into a
        reset (the read_image-variant pattern: mechanism, not prohibition).
        """
        return [
            *super().langchain_tools(no_images=no_images, resident=resident),
            *libero_tools.LIBERO_TOOLS,
            *(libero_tools.RESIDENT_TOOLS if resident else []),
        ]

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def _register_libero_tools(self) -> None:
        specs = self._SPECS
        # Inspection tools do not advance environment state. Most are stateless
        # module functions; segment is bound to the primitives-owned SAM3 client.
        # Plain handler functions, not the ``@tool``-wrapped versions exported
        # from ``libero_tools`` — those are StructuredTool objects for the
        # LangChain planner and are not directly callable with kwargs.
        inspection_handlers = {
            "view_driver_state": libero_state.view_driver_state,
            "view_camera_meta": libero_perception.view_camera_meta,
            "back_project": libero_perception.back_project,
            "segment": self._primitives.segment,
        }
        for name, handler in inspection_handlers.items():
            self.add_tool(name, specs[name], handler)
        # Primitive tools: each goes through _step, which looks up the
        # matching primitive method via getattr at call time.
        for name in libero_tools.PRIMITIVE_TOOL_NAMES:
            self.add_tool(name, specs[name], partial(self._step, name))

    def _step(self, name: str, **kwargs) -> dict:
        """Run ``self._primitives.<name>(**kwargs)``, dump the new step, and
        return the rendered state view + log.
        """
        command = {"action": name, **kwargs}
        t0 = time.time()
        start_frame = self._primitives.recorded_frame_count()
        try:
            result = getattr(self._primitives, name)(**kwargs)
            self.raise_if_cancelled()
        except ToolCancelled as exc:
            result = {
                "error": str(exc),
                "code": "tool_cancelled",
                "interrupted": True,
            }
        elapsed = round(time.time() - t0, 2)

        if isinstance(result, dict):
            result_dict = result
        else:
            result_dict = {"value": result}

        self._next_step += 1
        step_idx = self._next_step
        output_dir = get_output_dir()
        if self._dashboard_events.enabled:
            video_dir = libero_tools.artifact_path(output_dir, "action_videos")
            video_path = video_dir / f"step_{step_idx:02d}_{name}.mp4"
            try:
                self._primitives.save_frame_slice(start_frame, str(video_path), fps=20)
            except Exception as e:
                get_logger("libero_toolkit").warning(
                    f"failed to save action clip to {video_path}: {e}"
                )
        libero_tools.dump_state(
            self._primitives,
            str(output_dir),
            step_idx=step_idx,
            log={"command": command, "result": result_dict, "elapsed_s": elapsed},
        )
        out = libero_state.view_driver_state(step_idx)
        out["agent_elapsed_s"] = elapsed
        if result_dict.get("interrupted"):
            out.update(result_dict)
        return out

    def init_primitives_clean(
        self,
        *,
        primitives_kwargs: dict[str, Any],
    ) -> None:
        """Wipe stale run artifacts, build the LiberoPrimitives, dump step 0."""
        out_dir = get_output_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        for sub in libero_tools.ARTIFACT_DIRECTORIES:
            target = out_dir / sub
            if target.exists():
                shutil.rmtree(target)
        for target in (
            libero_tools.artifact_path(out_dir, "states"),
            libero_tools.artifact_path(out_dir, "metadata", camera="agentview", resolution="low"),
            libero_tools.artifact_path(out_dir, "episode_video"),
            # Per-run append-only records: a stale one left in place would make the
            # new episode's log read as a continuation of the previous run's.
            libero_tools.artifact_path(out_dir, "entities"),
            tool_log.path_for(out_dir),
        ):
            if target.exists():
                target.unlink()

        primitives = libero_tools.LiberoPrimitives(
            check_cancelled=self.raise_if_cancelled,
            **primitives_kwargs,
        )
        primitives.reset()
        primitives.start_recording()
        libero_tools.dump_state(primitives, str(out_dir), step_idx=0, log=None)
        self._dashboard_events.emit(
            ToolResultEvent(
                name="view_driver_state",
                result=libero_state.view_driver_state(0),
            )
        )

        self._primitives = primitives

    def close(self) -> None:
        """Flush the agent-side video buffer to disk (end-of-run).
        """
        if self._video_path is None:
            return
        try:
            self._primitives.stop_recording_and_save(self._video_path)
        except Exception as e:
            # The runner is in the cleanup path; never let a video save
            # abort it.
            get_logger("libero_toolkit").warning(
                f"failed to save video to {self._video_path}: {e}"
            )

    def write_recipe(self, recipe_tag: str) -> str:
        """Write the LIBERO recipe JSONL from the dumped state trace."""
        return libero_tools.write_recipe_from_states(str(get_output_dir()), recipe_tag)
