"""The LIBERO agent-facing tools, as native LangChain tools.

This module is the complete surface the planner sees: twelve ``@tool`` functions
whose docstrings are their descriptions and whose ``args_schema`` models live in
:mod:`robots.libero.tools.schemas`. Everything the model reads about a LIBERO
tool originates in those two files.

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

from robots.libero.tools import catalog, geometry, perception, state
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


@tool(args_schema=ViewDriverStateInput)
def view_driver_state(step: int | None = None) -> dict:
    """Read step NN from `states.json` + the matching state images in the output
    directory. If step is null, returns the latest entry. Each entry contains the
    robot state, libero_terminated flag, command log, and result. Returns
    available PNG paths in this stable order: 1) `images/image_NN.png` (Pi0-frame
    agentview), 2) `images_cam/image_cam_NN.png` (calibration-frame agentview),
    3) `images_wrist/image_wrist_NN.png` (calibration-frame wrist).
    High-resolution calibration-frame images are returned as file paths, not
    embedded as image bytes. Use the calibration-frame images for pixel
    back-projection; JSON state alone is not enough. Use agentview for global
    tabletop layout and object locations; use wrist for close-range details near
    the gripper, occlusions, and container/cabinet interiors.
    """
    return state.view_driver_state(step)


# ---------------------------------------------------------------------------
# motion — scripted OSC, no VLM call
# ---------------------------------------------------------------------------


@tool(args_schema=MoveToInput)
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
    """Scripted EEF servo to a world-frame XYZ target via the OSC controller.
    Holds orientation (use rotate_wrist / rotate_pitch / move_pose to reorient).
    gripper: -1 = open, +1 = close. NEVER command a single move_to with
    |Δxy| > 0.30 — OSC flips IK and the run corrupts; split long traversal into
    2-3 mid waypoints at carry z.
    """
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


@tool(args_schema=MovePoseInput)
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
    """Servo position AND orientation (pitch + yaw) SIMULTANEOUSLY. Unlike
    move_to (holds orientation) + rotate_pitch (holds xyz), this co-varies xyz
    and wrist tilt every env.step. Use to thread cabinet-front / low-shelf poses
    where a decoupled position servo drives the wrist into an IK singularity and
    stalls.
    """
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


@tool(args_schema=RotateWristInput)
def rotate_wrist(
    runtime: ToolRuntime,
    target_yaw: float | None = None,
    delta_yaw: float | None = None,
    gripper: float = 1.0,
    max_steps: int = 40,
    tol: float = 0.02,
    step_clip: float = 0.10,
) -> dict:
    """Rotate the wrist around the world Z-axis. Provide either target_yaw
    (absolute) or delta_yaw (relative). Holds xyz fixed.
    """
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


@tool(args_schema=RotatePitchInput)
def rotate_pitch(
    runtime: ToolRuntime,
    target_pitch: float | None = None,
    delta_pitch: float | None = None,
    gripper: float = 1.0,
    max_steps: int = 40,
    tol: float = 0.02,
    step_clip: float = 0.10,
) -> dict:
    """Tilt the gripper around the world X-axis. Provide either target_pitch
    (absolute) or delta_pitch (relative). Holds xyz and yaw fixed. Use before
    threading the gripper into a narrow opening whose front face normal is along
    world ±y (e.g. microwave cavity).
    """
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


@tool(args_schema=ReleaseInput)
def release(runtime: ToolRuntime, max_steps: int = 20) -> dict:
    """Open the gripper for up to max_steps env steps while holding EEF in place.
    Triggers libero termination if the matching On/In predicate is met.
    """
    ctx = _context(runtime)
    return ctx.advance("release", {"max_steps": max_steps}, ctx.primitives.release)


@tool(args_schema=SetGripperInput)
def set_gripper(
    runtime: ToolRuntime,
    gripper: float = -1.0,
    steps: int = 5,
) -> dict:
    """Hold the current EEF pose and drive the gripper command for `steps` env
    steps. Use to firm up a grip mid-carry.
    """
    ctx = _context(runtime)
    return ctx.advance(
        "set_gripper",
        {"gripper": gripper, "steps": steps},
        ctx.primitives.set_gripper,
    )


# ---------------------------------------------------------------------------
# vla — the only tools that call the Pi0.5 policy
# ---------------------------------------------------------------------------


@tool(args_schema=Pi0PickInput)
def pi0_pick(
    prompt: str,
    runtime: ToolRuntime,
    max_chunks: int = 24,
    lift_thresh: float = 0.05,
    gripper_closed_thresh: float = 0.06,
) -> dict:
    """Pi0.5 closed-loop pick. Use it for the grasp; YOU then do every move_to
    and release. Use modest max_chunks and verify the grasp from EEF lift,
    gripper closure, and available images.
    """
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


@tool(args_schema=Pi0DoubledInput)
def pi0_doubled(
    prompt: str,
    runtime: ToolRuntime,
    max_chunks: int = 20,
) -> dict:
    """Pi0.5 closed-loop contact skill for non-pick interactions (e.g.
    stove/knob/button/short push). Returned success/task_success only mirrors
    official libero_terminated; for intermediate contact skills, success=false
    does not necessarily mean the contact interaction failed. Inspect image/state
    evidence. Do not use it as a general pick/place shortcut.
    """
    ctx = _context(runtime)
    return ctx.advance(
        "pi0_doubled",
        {"prompt": prompt, "max_chunks": max_chunks},
        ctx.primitives.pi0_doubled,
    )


# ---------------------------------------------------------------------------
# perception — read-only over already-dumped artifacts
# ---------------------------------------------------------------------------


@tool(args_schema=ViewCameraMetaInput)
def view_camera_meta(camera: str = "agentview", step: int | None = None) -> dict:
    """Read camera calibration metadata from the output dir.
    camera='agentview' reads static camera_meta.json. camera='wrist' reads the
    per-step wrist metadata.
    """
    return perception.view_camera_meta(camera, step)


@tool(args_schema=SegmentInput)
def segment(
    runtime: ToolRuntime,
    prompt: str = "",
    camera: str = "agentview",
    step: int | None = None,
    point: list[int] | None = None,
    min_score: float = 0.2,
    entity: str = "",
) -> dict:
    """SAM3 visual segmentation over an existing run artifact. It never renders a
    new camera view. Provide exactly one text prompt or single positive point. A
    successful top-ranked mask is projected through the matching world map to
    produce world_xyz, plus geometry that world_xyz alone cannot carry:

    world_xyz is a per-axis median of the mask's visible points -- for a hollow
    container (basket, bowl, drawer) this sits on the visible near wall, not the
    opening centre, and using it as a drop-off point biases the release toward
    the camera. When present, prefer these instead:
    - rim.xy_bbox_center + rim.retreat_direction: the opening's bounding-box
      centre, plus which way to move off the wall nearest the camera. Measured
      on 23 finished placement attempts: successful releases sat 1.2-9.3 cm on
      the far side of world_xyz along this direction; failures sat within
      1.3 cm of world_xyz.
    - interior.xy_median: the floor seen through the opening, when visible.
    - bbox_3d.extent: the mask's 3D bounding box, AXIS-ALIGNED -- so for an
      object lying at an angle all three extents are diagonals of a box that
      fits nothing. Prefer `shape` below whenever it is present.
    - shape: the box fitted to the points instead of to the world axes, which is
      what a grasp needs. shape.footprint.short_extent_m (= graspable_width_m) is
      the width the fingers must span, and short_axis_yaw_deg is the direction
      they travel; long_axis_yaw_deg is the object's long axis. Yaw is an AXIS
      folded into [-90, 90), so either way along it is equally valid. It is NOT a
      rotate_wrist argument -- which eef axis the fingers close along is gripper
      geometry, so verify that mapping once and reuse it. Check
      yaw_is_meaningful first: a near-round footprint (bowl, can) has no
      meaningful axis. shape.orientation ('upright' / 'lying' / 'ambiguous')
      separates a toppled object from a standing one better than raw extents.
    - looks_hollow: true when the mask reads as a ring enclosing a lower
      middle (a container) rather than a solid body with a raised cap (a
      bottle) -- height alone cannot tell these apart.

    Call world_extent(mode="held_object") after a pick and before a release to
    get the grasped object's actual offset from the end-effector; move_to
    commands the end-effector, not the object, and the offset is not constant
    across grasps.

    Pass `entity` to register this reading under a name you choose. Readings are
    append-only: a later segment of the same entity adds to its history instead of
    replacing it, so a motion can always cite the reading it was planned from.
    Every subsequent tool result then carries that entity's latest position and a
    stale_reason for it. Re-segment anything whose stale_reason is not 'fresh'
    before committing a motion to it, and resolve any identity_warning before
    committing a grasp.
    """
    ctx = _context(runtime)
    return ctx.primitives.segment(
        prompt=prompt,
        camera=camera,
        step=step,
        point=point,
        min_score=min_score,
        entity=entity,
    )


@tool(args_schema=BackProjectInput)
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
    """Back-project a pixel (row, col) to a world XYZ point using the selected
    camera's precomputed world map. Row 0 = top of image, col 0 = left. Returns
    world_xyz in meters.

    USE THIS to find where an object is in the world — look at the
    high-resolution paths returned by view_driver_state to pick a pixel on the
    target object, then call back_project. The default resolution is high
    (1024x1024). Pass resolution='low' only for pixels from the
    embedded/standard 256 image. The pixel coordinates must come from the same
    camera and resolution requested here. Use camera='agentview' for global
    tabletop layout and object locations; use camera='wrist' for close-range
    details near the gripper, occlusions, and container/cabinet interiors. Sample
    several pixels on the object and median their xy for robustness.

    REGION MODE: pass row_range=[r0,r1] and col_range=[c0,c1] instead of row/col
    to get the midpoint of world xy over that pixel window, with an optional
    world-z band (z_min, z_max). Use it for the center of a container cavity or
    flat region, where a single-pixel or mask-median estimate is biased toward an
    edge/rim.
    """
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


@tool(args_schema=WorldExtentInput)
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
    """Query occupied space inside a world-frame box, fusing both cameras.

    Both world maps already hold WORLD coordinates, so fusing them is a
    concatenation with no registration step (measured agreement on the shared
    table plane is ~3 mm). Use mode='occupancy' to locate a container wall or
    check reachable space before a move -- it reports the nearest occupied
    surface along each axis from the box centre, which is what a container's
    wall position looks like in this representation. Use mode='held_object'
    after a pick, before a release, to get the grasped object's actual offset
    from the end-effector: move_to commands the end-effector, not the object,
    and that offset is not a fixed constant across grasps.

    This is read-only and never advances the environment or renders a new
    view, the same as back_project.
    """
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


@tool(args_schema=CompareExtentInput)
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
    """Diff the occupied space inside a world-frame box between two steps.

    Use this to VERIFY that an action did what you intended, without going
    through segmentation. Every step's world map is already on disk, so "did
    anything change here" is a geometry question, not a recognition one — it does
    not depend on SAM3 grounding a noun, and it works when you cannot inspect the
    images yourself.

    What it answers well:
    - did the object I released actually land inside the container? Box the
      container's interior and compare the step before the release with the step
      after; look for voxels_added there.
    - did the object I meant to pick actually leave the table? Box where it was
      and look for voxels_removed.
    - did I disturb something I was not aiming at? Box that thing and check that
      the delta is near zero.

    Voxels are compared as SETS, so added and removed space are reported
    separately: a single net count can be zero while everything inside moved.

    ⚠ Occlusion is the trap. Space empties either because the object left, or
    because the arm now stands between the camera and it, and no diff of two
    clouds can separate those. Check n_points_in_box at both steps first: a large
    drop there alongside a large voxels_removed is as consistent with a new
    occlusion as with a moved object. Treat a removal as evidence only when the
    point count held up.

    Read-only: never advances the environment and never renders a new view.
    """
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
