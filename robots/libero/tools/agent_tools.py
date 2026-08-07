"""The LIBERO agent-facing tools, as native LangChain tools.

This module is the complete surface the planner sees: fourteen ``@tool``
functions whose model-facing descriptions render from the structured entries
in :mod:`robots.libero.tools.tool_docs` and whose ``args_schema`` models live
in :mod:`robots.libero.tools.schemas`. Everything the model reads about a
LIBERO tool originates in those two files; docstrings here are developer
notes only.

Each function is a thin, explicit call into the primitives — no name-string
dispatch, no registry indirection. Env-advancing tools route through
:meth:`LiberoContext.advance`, which owns the per-action bookkeeping; read-only
tools call their handler directly and never touch the environment.

Live handles arrive through ``ToolRuntime``: ``runtime.context`` is the run's
:class:`LiberoContext`. Tools that need no live handle (``view_driver_state``,
``view_camera_meta``, ``back_project``) omit the parameter entirely and stay
callable outside a graph.

⚠ This module must NOT use ``from __future__ import annotations``. LangChain
detects the ``ToolRuntime`` parameter by resolving the annotation to the actual
type; under PEP 563 the annotation is the *string* ``"ToolRuntime"``, detection
silently fails, and every call dies with ``missing 1 required positional
argument: 'runtime'`` at dispatch time rather than at import. Verified against
langchain-core 1.5.3 / langgraph 1.2.10. Keep the annotations eager here —
``X | None`` and ``list[float]`` evaluate fine on the supported Pythons (>=3.10).
"""

from langchain.tools import ToolRuntime, tool

from robots.libero.tools import catalog, geometry, perception, state, tool_docs
from robots.libero.tools.context import LiberoContext
from robots.libero.tools.schemas import (
    BackProjectInput,
    CompareExtentInput,
    MovePoseInput,
    MoveToInput,
    Pi0DoubledInput,
    Pi0PickInput,
    ReleaseInput,
    RotatePitchInput,
    RotateWristInput,
    SegmentInput,
    SetGripperInput,
    ViewCameraMetaInput,
    ViewDriverStateInput,
    WorldExtentInput,
)


def _context(runtime: ToolRuntime) -> LiberoContext:
    """Return the run's context, failing loudly if it was never provided."""
    ctx = runtime.context
    if not isinstance(ctx, LiberoContext):
        raise RuntimeError(
            "LIBERO tools require a LiberoContext as the graph context; got "
            f"{type(ctx).__name__}"
        )
    return ctx


# ---------------------------------------------------------------------------
# state
# ---------------------------------------------------------------------------


@tool(
    args_schema=ViewDriverStateInput,
    description=tool_docs.render_description("view_driver_state"),
)
def view_driver_state(step: int | None = None) -> dict:
    """Model-facing text renders from ``tool_docs`` — edit it there."""
    return state.view_driver_state(step)


# ---------------------------------------------------------------------------
# motion — scripted OSC, no VLM call
# ---------------------------------------------------------------------------


@tool(args_schema=MoveToInput, description=tool_docs.render_description("move_to"))
def move_to(
    xyz: list[float],
    runtime: ToolRuntime,
    gripper: float = -1.0,
    tol: float = 0.012,
    step_clip: float = 0.025,
    max_steps: int = 80,
    action_scale: float = 0.05,
    target_yaw: float | None = None,
    yaw_step_clip: float = 0.10,
) -> dict:
    """Model-facing text renders from ``tool_docs`` — edit it there."""
    ctx = _context(runtime)
    return ctx.advance(
        "move_to",
        {
            "xyz": xyz,
            "max_steps": max_steps,
            "gripper": gripper,
            "step_clip": step_clip,
            "tol": tol,
            "action_scale": action_scale,
            "target_yaw": target_yaw,
            "yaw_step_clip": yaw_step_clip,
        },
        ctx.primitives.move_to,
    )


@tool(args_schema=MovePoseInput, description=tool_docs.render_description("move_pose"))
def move_pose(
    xyz: list[float],
    runtime: ToolRuntime,
    target_pitch: float | None = None,
    target_yaw: float | None = None,
    gripper: float = -1.0,
    step_clip: float = 0.02,
    pitch_step: float = 0.08,
    yaw_step: float = 0.08,
    tol: float = 0.012,
    ori_tol: float = 0.05,
    action_scale: float = 0.05,
    max_steps: int = 150,
) -> dict:
    """Model-facing text renders from ``tool_docs`` — edit it there."""
    ctx = _context(runtime)
    return ctx.advance(
        "move_pose",
        {
            "xyz": xyz,
            "target_pitch": target_pitch,
            "target_yaw": target_yaw,
            "gripper": gripper,
            "step_clip": step_clip,
            "pitch_step": pitch_step,
            "yaw_step": yaw_step,
            "tol": tol,
            "ori_tol": ori_tol,
            "action_scale": action_scale,
            "max_steps": max_steps,
        },
        ctx.primitives.move_pose,
    )


@tool(
    args_schema=RotateWristInput,
    description=tool_docs.render_description("rotate_wrist"),
)
def rotate_wrist(
    runtime: ToolRuntime,
    target_yaw: float | None = None,
    delta_yaw: float | None = None,
    gripper: float = 1.0,
    max_steps: int = 40,
    tol: float = 0.02,
    step_clip: float = 0.10,
) -> dict:
    """Model-facing text renders from ``tool_docs`` — edit it there."""
    ctx = _context(runtime)
    return ctx.advance(
        "rotate_wrist",
        {
            "target_yaw": target_yaw,
            "delta_yaw": delta_yaw,
            "gripper": gripper,
            "max_steps": max_steps,
            "tol": tol,
            "step_clip": step_clip,
        },
        ctx.primitives.rotate_wrist,
    )


@tool(
    args_schema=RotatePitchInput,
    description=tool_docs.render_description("rotate_pitch"),
)
def rotate_pitch(
    runtime: ToolRuntime,
    target_pitch: float | None = None,
    delta_pitch: float | None = None,
    gripper: float = 1.0,
    max_steps: int = 40,
    tol: float = 0.02,
    step_clip: float = 0.10,
) -> dict:
    """Model-facing text renders from ``tool_docs`` — edit it there."""
    ctx = _context(runtime)
    return ctx.advance(
        "rotate_pitch",
        {
            "target_pitch": target_pitch,
            "delta_pitch": delta_pitch,
            "gripper": gripper,
            "max_steps": max_steps,
            "tol": tol,
            "step_clip": step_clip,
        },
        ctx.primitives.rotate_pitch,
    )


@tool(args_schema=ReleaseInput, description=tool_docs.render_description("release"))
def release(runtime: ToolRuntime, max_steps: int = 20) -> dict:
    """Model-facing text renders from ``tool_docs`` — edit it there."""
    ctx = _context(runtime)
    return ctx.advance("release", {"max_steps": max_steps}, ctx.primitives.release)


@tool(
    args_schema=SetGripperInput,
    description=tool_docs.render_description("set_gripper"),
)
def set_gripper(
    runtime: ToolRuntime,
    gripper: float = -1.0,
    steps: int = 5,
) -> dict:
    """Model-facing text renders from ``tool_docs`` — edit it there."""
    ctx = _context(runtime)
    return ctx.advance(
        "set_gripper",
        {"gripper": gripper, "steps": steps},
        ctx.primitives.set_gripper,
    )


# ---------------------------------------------------------------------------
# vla — the only tools that call the Pi0.5 policy
# ---------------------------------------------------------------------------


@tool(args_schema=Pi0PickInput, description=tool_docs.render_description("pi0_pick"))
def pi0_pick(
    prompt: str,
    runtime: ToolRuntime,
    max_chunks: int = 24,
    lift_thresh: float = 0.05,
    gripper_closed_thresh: float = 0.06,
) -> dict:
    """Model-facing text renders from ``tool_docs`` — edit it there."""
    ctx = _context(runtime)
    return ctx.advance(
        "pi0_pick",
        {
            "prompt": prompt,
            "max_chunks": max_chunks,
            "lift_thresh": lift_thresh,
            "gripper_closed_thresh": gripper_closed_thresh,
        },
        ctx.primitives.pi0_pick,
    )


@tool(
    args_schema=Pi0DoubledInput,
    description=tool_docs.render_description("pi0_doubled"),
)
def pi0_doubled(
    prompt: str,
    runtime: ToolRuntime,
    max_chunks: int = 20,
) -> dict:
    """Model-facing text renders from ``tool_docs`` — edit it there."""
    ctx = _context(runtime)
    return ctx.advance(
        "pi0_doubled",
        {"prompt": prompt, "max_chunks": max_chunks},
        ctx.primitives.pi0_doubled,
    )


# ---------------------------------------------------------------------------
# perception — read-only over already-dumped artifacts
# ---------------------------------------------------------------------------


@tool(
    args_schema=ViewCameraMetaInput,
    description=tool_docs.render_description("view_camera_meta"),
)
def view_camera_meta(camera: str = "agentview", step: int | None = None) -> dict:
    """Model-facing text renders from ``tool_docs`` — edit it there."""
    return perception.view_camera_meta(camera, step)


@tool(args_schema=SegmentInput, description=tool_docs.render_description("segment"))
def segment(
    runtime: ToolRuntime,
    prompt: str = "",
    camera: str = "agentview",
    step: int | None = None,
    point: list[int] | None = None,
    min_score: float = 0.2,
    entity: str = "",
) -> dict:
    """Model-facing text renders from ``tool_docs`` — edit it there."""
    ctx = _context(runtime)
    return ctx.primitives.segment(
        prompt=prompt,
        camera=camera,
        step=step,
        point=point,
        min_score=min_score,
        entity=entity,
    )


@tool(
    args_schema=BackProjectInput,
    description=tool_docs.render_description("back_project"),
)
def back_project(
    row: int | None = None,
    col: int | None = None,
    step: int | None = None,
    camera: str = "agentview",
    resolution: str = "high",
    row_range: list[int] | None = None,
    col_range: list[int] | None = None,
    z_min: float | None = None,
    z_max: float | None = None,
) -> dict:
    """Model-facing text renders from ``tool_docs`` — edit it there."""
    return perception.back_project(
        row=row,
        col=col,
        step=step,
        camera=camera,
        resolution=resolution,
        row_range=row_range,
        col_range=col_range,
        z_min=z_min,
        z_max=z_max,
    )


@tool(
    args_schema=WorldExtentInput,
    description=tool_docs.render_description("world_extent"),
)
def world_extent(
    x_range: list[float] | None = None,
    y_range: list[float] | None = None,
    z_range: list[float] | None = None,
    step: int | None = None,
    cameras: str = "fused",
    voxel: float = 0.01,
    exclude_arm_radius: float = 0.12,
    mode: str = "occupancy",
) -> dict:
    """Model-facing text renders from ``tool_docs`` — edit it there."""
    return geometry.world_extent(
        x_range=x_range,
        y_range=y_range,
        z_range=z_range,
        step=step,
        cameras=cameras,
        voxel=voxel,
        exclude_arm_radius=exclude_arm_radius,
        mode=mode,
    )


@tool(
    args_schema=CompareExtentInput,
    description=tool_docs.render_description("compare_extent"),
)
def compare_extent(
    x_range: list[float] | None = None,
    y_range: list[float] | None = None,
    z_range: list[float] | None = None,
    step_a: int | None = None,
    step_b: int | None = None,
    cameras: str = "fused",
    voxel: float = 0.01,
    exclude_arm_radius: float = 0.12,
) -> dict:
    """Model-facing text renders from ``tool_docs`` — edit it there."""
    return geometry.compare_extent(
        x_range=x_range,
        y_range=y_range,
        z_range=z_range,
        step_a=step_a,
        step_b=step_b,
        cameras=cameras,
        voxel=voxel,
        exclude_arm_radius=exclude_arm_radius,
    )


# ---------------------------------------------------------------------------
# Collections, grouped by kind
# ---------------------------------------------------------------------------

STATE_TOOLS = [view_driver_state]
MOTION_TOOLS = [move_to, move_pose, rotate_wrist, rotate_pitch, release, set_gripper]
VLA_TOOLS = [pi0_pick, pi0_doubled]
PERCEPTION_TOOLS = [view_camera_meta, segment, back_project, world_extent,
                    compare_extent]

#: Tools that advance the environment. Anything here mutates world state, so a
#: gate or a fresh-observation obligation belongs on this set, not on the rest.
ADVANCING_TOOLS = [*MOTION_TOOLS, *VLA_TOOLS]

#: Read-only tools: safe to call without changing the environment.
READ_ONLY_TOOLS = [*STATE_TOOLS, *PERCEPTION_TOOLS]

LIBERO_TOOLS = [*READ_ONLY_TOOLS, *ADVANCING_TOOLS]

TOOLS_BY_KIND = {
    catalog.STATE: STATE_TOOLS,
    catalog.MOTION: MOTION_TOOLS,
    catalog.VLA: VLA_TOOLS,
    catalog.PERCEPTION: PERCEPTION_TOOLS,
}


def _check_invariants() -> None:
    """Fail at import time if the tool lists and the catalog disagree."""
    names = [t.name for t in LIBERO_TOOLS]
    if len(set(names)) != len(names):
        raise RuntimeError(f"duplicate LIBERO tool name in {names}")
    advancing = {t.name for t in ADVANCING_TOOLS}
    if advancing != set(catalog.PRIMITIVE_TOOL_NAMES):
        raise RuntimeError(
            "ADVANCING_TOOLS disagrees with catalog.PRIMITIVE_TOOL_NAMES: "
            f"{sorted(advancing ^ set(catalog.PRIMITIVE_TOOL_NAMES))}"
        )


_check_invariants()
