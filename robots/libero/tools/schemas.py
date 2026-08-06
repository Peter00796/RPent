"""Pydantic input schemas for the LIBERO agent tools.

One model per tool, grouped by tool kind. These are the single source of truth
for what the planner may pass: ``@tool(args_schema=...)`` renders the JSON
Schema from them, and Pydantic validates every call before the handler runs.

Field descriptions are part of the model-facing surface — they are injected into
the planner's context alongside the tool description, so treat edits here the
same as edits to a prompt.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Camera = Literal["agentview", "wrist"]

# ---------------------------------------------------------------------------
# state
# ---------------------------------------------------------------------------


class ViewDriverStateInput(BaseModel):
    """Select which dumped step to read back."""

    step: int | None = Field(
        default=None,
        description="Step number; 0 = initial. Null = latest.",
    )


# ---------------------------------------------------------------------------
# motion — scripted OSC primitives
# ---------------------------------------------------------------------------


class MoveToInput(BaseModel):
    """Target pose and servo limits for a position-only move."""

    xyz: list[float] = Field(
        description="World-frame target [x, y, z] in meters",
        min_length=3,
        max_length=3,
    )
    gripper: float = Field(
        default=-1.0,
        description="Gripper command: -1 open, +1 close (default -1)",
    )
    tol: float = Field(default=0.012, description="Position tolerance, m (default 0.012)")
    step_clip: float = Field(
        default=0.025,
        description="Per-step Δxyz cap before action_scale, m (default 0.025)",
    )
    max_steps: int = Field(default=80, description="Step budget (default 80)")
    action_scale: float = Field(default=0.05, description="OSC action scale (default 0.05)")
    target_yaw: float | None = Field(
        default=None,
        description="Optional world-frame yaw target in radians",
    )
    yaw_step_clip: float = Field(
        default=0.10,
        description="Per-step yaw clip, rad (default 0.10)",
    )


class MovePoseInput(BaseModel):
    """Target pose and servo limits for a coupled position+orientation move."""

    xyz: list[float] = Field(
        description="World-frame target [x, y, z] in meters",
        min_length=3,
        max_length=3,
    )
    target_pitch: float | None = Field(default=None, description="Absolute pitch target, rad")
    target_yaw: float | None = Field(default=None, description="Absolute yaw target, rad")
    gripper: float = Field(
        default=-1.0,
        description="Gripper command held during the move (default -1)",
    )
    step_clip: float = Field(default=0.02, description="Per-step Δxyz cap, m (default 0.02)")
    pitch_step: float = Field(default=0.08, description="Per-step pitch clip, rad (default 0.08)")
    yaw_step: float = Field(default=0.08, description="Per-step yaw clip, rad (default 0.08)")
    tol: float = Field(default=0.012, description="Position tolerance, m (default 0.012)")
    ori_tol: float = Field(default=0.05, description="Orientation tolerance, rad (default 0.05)")
    action_scale: float = Field(default=0.05, description="OSC action scale (default 0.05)")
    max_steps: int = Field(default=150, description="Step budget (default 150)")


class RotateWristInput(BaseModel):
    """Absolute or relative wrist yaw goal. Provide exactly one of the two."""

    target_yaw: float | None = Field(
        default=None,
        description="Absolute world-frame yaw target, rad",
    )
    delta_yaw: float | None = Field(default=None, description="Relative yaw delta, rad")
    gripper: float = Field(
        default=1.0,
        description="Gripper command held during rotation (default +1)",
    )
    max_steps: int = Field(default=40, description="Step budget (default 40)")
    tol: float = Field(default=0.02, description="Yaw tolerance, rad (default 0.02)")
    step_clip: float = Field(default=0.10, description="Per-step yaw clip, rad (default 0.10)")


class RotatePitchInput(BaseModel):
    """Absolute or relative gripper pitch goal. Provide exactly one of the two."""

    target_pitch: float | None = Field(
        default=None,
        description="Absolute world-frame pitch target, rad",
    )
    delta_pitch: float | None = Field(default=None, description="Relative pitch delta, rad")
    gripper: float = Field(
        default=1.0,
        description="Gripper command held during rotation (default +1)",
    )
    max_steps: int = Field(default=40, description="Step budget (default 40)")
    tol: float = Field(default=0.02, description="Pitch tolerance, rad (default 0.02)")
    step_clip: float = Field(default=0.10, description="Per-step pitch clip, rad (default 0.10)")


class ReleaseInput(BaseModel):
    """Step budget for holding the gripper open in place."""

    max_steps: int = Field(default=20, description="Step budget (default 20)")


class SetGripperInput(BaseModel):
    """Gripper command to hold, and for how many env steps."""

    gripper: float = Field(
        default=-1.0,
        description="Gripper command: -1 open, +1 close (default -1)",
    )
    steps: int = Field(default=5, description="Number of env steps (default 5)")


# ---------------------------------------------------------------------------
# vla — Pi0.5 closed-loop primitives
# ---------------------------------------------------------------------------


class Pi0PickInput(BaseModel):
    """Pi0 instruction and the success thresholds for a closed-loop pick."""

    prompt: str = Field(
        description="Pi0 prompt (e.g. 'pick up the akita black bowl').",
    )
    max_chunks: int = Field(default=24, description="Action-chunk budget (default 24)")
    lift_thresh: float = Field(
        default=0.05,
        description=(
            "EEF post-descent ascent threshold for success, m (default 0.05)"
        ),
    )
    gripper_closed_thresh: float = Field(
        default=0.06,
        description="Finger-separation closed threshold (default 0.06)",
    )


class Pi0DoubledInput(BaseModel):
    """Pi0 instruction and budget for a non-pick contact skill."""

    prompt: str = Field(
        description="Contact-skill prompt, e.g. 'turn on the stove'.",
    )
    max_chunks: int = Field(default=20, description="Action-chunk budget (default 20)")


# ---------------------------------------------------------------------------
# perception — read-only over already-dumped artifacts
# ---------------------------------------------------------------------------


class ViewCameraMetaInput(BaseModel):
    """Which camera's calibration metadata to read."""

    camera: Camera = Field(
        default="agentview",
        description="Camera metadata to read (default agentview).",
    )
    step: int | None = Field(
        default=None,
        description="Wrist metadata step to use (default latest).",
    )


class SegmentInput(BaseModel):
    """A SAM3 query: exactly one of ``prompt`` or ``point``."""

    prompt: str = Field(default="", description="Object/text prompt to segment.")
    camera: Camera = Field(
        default="agentview",
        description="Artifact camera to use (default agentview).",
    )
    step: int | None = Field(
        default=None,
        description="Step NN to segment; null = latest.",
    )
    point: list[int] | None = Field(
        default=None,
        description=(
            "Optional single positive point as [row, col]. "
            "Mutually exclusive with prompt."
        ),
        min_length=2,
        max_length=2,
    )
    min_score: float = Field(
        default=0.2,
        description="Minimum accepted mask score (default 0.2).",
    )
    entity: str = Field(
        default="",
        description=(
            "Optional name to register this reading under, e.g. "
            "'bowl_on_cookie_box' or 'basket_cavity'. Name it for what it IS and "
            "where it is, not by an internal object id — two identical objects "
            "have indistinguishable names but different relations. Registering "
            "adds the reading to the run's entity index (append-only: a later "
            "segment adds a reading, never overwrites one), so subsequent tool "
            "results report its position and how stale that position is. Omit to "
            "run a one-off lookup that is not registered."
        ),
    )


class BackProjectInput(BaseModel):
    """A pixel or a pixel window to look up in a world map."""

    row: int | None = Field(
        default=None,
        description="Pixel row (0=top) in the selected resolution image.",
    )
    col: int | None = Field(
        default=None,
        description="Pixel column (0=left) in the selected resolution image.",
    )
    step: int | None = Field(
        default=None,
        description="Depth/world-map step to use (default latest). 0 for initial.",
    )
    camera: Camera = Field(
        default="agentview",
        description="Camera to back-project from (default agentview).",
    )
    resolution: Literal["high", "low"] = Field(
        default="high",
        description=(
            "Coordinate system for row/col (default high). "
            "Use low only when row/col came from the "
            "embedded/standard 256 image."
        ),
    )
    row_range: list[int] | None = Field(
        default=None,
        description="Region mode: [r0, r1] pixel row window. Requires col_range.",
        min_length=2,
        max_length=2,
    )
    col_range: list[int] | None = Field(
        default=None,
        description="Region mode: [c0, c1] pixel col window. Requires row_range.",
        min_length=2,
        max_length=2,
    )
    z_min: float | None = Field(
        default=None,
        description="Region mode: keep only pixels with world z >= z_min.",
    )
    z_max: float | None = Field(
        default=None,
        description="Region mode: keep only pixels with world z <= z_max.",
    )


class CompareExtentInput(BaseModel):
    """A world-frame box, and the two steps to compare occupancy between."""

    x_range: list[float] | None = Field(
        default=None,
        description="[min, max] world x bound in metres. Default is wide-open.",
        min_length=2,
        max_length=2,
    )
    y_range: list[float] | None = Field(
        default=None,
        description="[min, max] world y bound in metres. Default is wide-open.",
        min_length=2,
        max_length=2,
    )
    z_range: list[float] | None = Field(
        default=None,
        description="[min, max] world z bound in metres. Default excludes the table.",
        min_length=2,
        max_length=2,
    )
    step_a: int | None = Field(
        default=None,
        description="Earlier step to compare from. Default 0, the initial scene.",
    )
    step_b: int | None = Field(
        default=None,
        description="Later step to compare to. Default is the latest step.",
    )
    cameras: Literal["fused", "agentview", "wrist"] = Field(
        default="fused",
        description=(
            "Which camera's world map(s) to compare. 'fused' concatenates both "
            "clouds with no registration step (they already share the world "
            "frame)."
        ),
    )
    voxel: float = Field(
        default=0.01,
        description="Voxel edge length in metres for the comparison (0.002-0.05).",
    )
    exclude_arm_radius: float = Field(
        default=0.12,
        description=(
            "Drop points within this many metres of that step's end-effector "
            "position before comparing, so the manipulator's own body is not "
            "counted as a change. Applied per step with each step's own pose."
        ),
    )


class WorldExtentInput(BaseModel):
    """A world-frame box to query for occupied space, fusing both cameras."""

    x_range: list[float] | None = Field(
        default=None,
        description="[min, max] world x bound in metres. Default is wide-open.",
        min_length=2,
        max_length=2,
    )
    y_range: list[float] | None = Field(
        default=None,
        description="[min, max] world y bound in metres. Default is wide-open.",
        min_length=2,
        max_length=2,
    )
    z_range: list[float] | None = Field(
        default=None,
        description="[min, max] world z bound in metres. Default excludes the table.",
        min_length=2,
        max_length=2,
    )
    step: int | None = Field(
        default=None,
        description="World-map step to use (default latest). 0 for initial.",
    )
    cameras: Literal["fused", "agentview", "wrist"] = Field(
        default="fused",
        description=(
            "Which camera's world map(s) to query. 'fused' concatenates both "
            "clouds with no registration step (they already share the world "
            "frame); use it unless you have a reason to isolate one camera."
        ),
    )
    voxel: float = Field(
        default=0.01,
        description="Voxel edge length in metres for occupancy counting (0.002-0.05).",
    )
    exclude_arm_radius: float = Field(
        default=0.12,
        description=(
            "Drop points within this many metres of the current end-effector "
            "position before counting occupancy, so the manipulator's own body "
            "is not reported as an obstacle."
        ),
    )
    mode: Literal["occupancy", "held_object"] = Field(
        default="occupancy",
        description=(
            "'occupancy': voxel-count the box and report the nearest occupied "
            "surface along each axis from the box centre -- use this to locate "
            "a container wall or check reachable space before a move. "
            "'held_object': estimate the grasped object's centroid and its xy "
            "offset from the end-effector -- use this before releasing, since "
            "move_to commands the end-effector, not the object it is holding, "
            "and the offset is not a fixed constant."
        ),
    )
