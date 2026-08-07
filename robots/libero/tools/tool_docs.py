"""Structured, model-facing descriptions for the 14 LIBERO tools.

Single source of truth: :mod:`robots.libero.tools.agent_tools` renders each
``@tool``'s description from the entries here (its docstrings are developer
notes only). Argument descriptions stay in :mod:`robots.libero.tools.schemas`
and are never restated here.

The template and renderer are shared with the common tools — see
:mod:`rpent.tools.tool_docs` for the field definitions (what / need / returns /
when / how / failure_modes) and the hard constraints the lint enforces.

CONTENT IS MIGRATED VERBATIM from the pre-migration docstrings: the sentences
were moved into fields, not reworded. The model-facing surface is an
experiment variable — a wording change here is a description edit that must be
made deliberately and measured, never smuggled in with a refactor. The
quantitative caveats (|Δxy| > 0.30, the 23-placement rim study, the 50x
whole-episode voxel swing) all have measurement backing recorded in
docs/harness/.

This module is dependency-free beyond the shared renderer, so the lint can
load it by file path without importing the tool layer (and its langchain
dependency).
"""
from __future__ import annotations

from rpent.tools.tool_docs import render_doc, validate_docs

LIBERO_TOOL_DOCS: dict[str, dict[str, object]] = {
    # -- state ---------------------------------------------------------------
    "view_driver_state": {
        "what": (
            "Read step NN from `states.json` + the matching state images in "
            "the output directory. If step is null, returns the latest entry."
        ),
        "returns": (
            "Each entry contains the robot state, libero_terminated flag, "
            "command log, and result. Returns available PNG paths in this "
            "stable order: 1) `images/image_NN.png` (Pi0-frame agentview), "
            "2) `images_cam/image_cam_NN.png` (calibration-frame agentview), "
            "3) `images_wrist/image_wrist_NN.png` (calibration-frame wrist). "
            "High-resolution calibration-frame images are returned as file "
            "paths, not embedded as image bytes."
        ),
        "when": (
            "Use the calibration-frame images for pixel back-projection; JSON "
            "state alone is not enough. Use agentview for global tabletop "
            "layout and object locations; use wrist for close-range details "
            "near the gripper, occlusions, and container/cabinet interiors."
        ),
    },
    # -- motion --------------------------------------------------------------
    "move_to": {
        "what": (
            "Scripted EEF servo to a world-frame XYZ target via the OSC "
            "controller. Holds orientation (use rotate_wrist / rotate_pitch / "
            "move_pose to reorient). gripper: -1 = open, +1 = close."
        ),
        "failure_modes": (
            "NEVER command a single move_to with |Δxy| > 0.30 — OSC flips IK "
            "and the run corrupts; split long traversal into 2-3 mid waypoints "
            "at carry z."
        ),
    },
    "move_pose": {
        "what": (
            "Servo position AND orientation (pitch + yaw) SIMULTANEOUSLY. "
            "Unlike move_to (holds orientation) + rotate_pitch (holds xyz), "
            "this co-varies xyz and wrist tilt every env.step."
        ),
        "when": (
            "thread cabinet-front / low-shelf poses where a decoupled position "
            "servo drives the wrist into an IK singularity and stalls."
        ),
    },
    "rotate_wrist": {
        "what": (
            "Rotate the wrist around the world Z-axis. Provide either "
            "target_yaw (absolute) or delta_yaw (relative). Holds xyz fixed."
        ),
    },
    "rotate_pitch": {
        "what": (
            "Tilt the gripper around the world X-axis. Provide either "
            "target_pitch (absolute) or delta_pitch (relative). Holds xyz and "
            "yaw fixed."
        ),
        "when": (
            "before threading the gripper into a narrow opening whose front "
            "face normal is along world ±y (e.g. microwave cavity)."
        ),
    },
    "release": {
        "what": (
            "Open the gripper for up to max_steps env steps while holding EEF "
            "in place. Triggers libero termination if the matching On/In "
            "predicate is met."
        ),
    },
    "set_gripper": {
        "what": (
            "Hold the current EEF pose and drive the gripper command for "
            "`steps` env steps."
        ),
        "when": "firm up a grip mid-carry.",
    },
    # -- vla -----------------------------------------------------------------
    "pi0_pick": {
        "what": (
            "Pi0.5 closed-loop pick. Use it for the grasp; YOU then do every "
            "move_to and release."
        ),
        "how": (
            "Use modest max_chunks and verify the grasp from EEF lift, gripper "
            "closure, and available images."
        ),
    },
    "pi0_doubled": {
        "what": (
            "Pi0.5 closed-loop contact skill for non-pick interactions (e.g. "
            "stove/knob/button/short push)."
        ),
        "returns": (
            "Returned success/task_success only mirrors official "
            "libero_terminated; for intermediate contact skills, success=false "
            "does not necessarily mean the contact interaction failed. Inspect "
            "image/state evidence."
        ),
        "when": "Do not use it as a general pick/place shortcut.",
    },
    # -- perception ----------------------------------------------------------
    "view_camera_meta": {
        "what": (
            "Read camera calibration metadata from the output dir. "
            "camera='agentview' reads static camera_meta.json. camera='wrist' "
            "reads the per-step wrist metadata."
        ),
    },
    "segment": {
        "what": (
            "SAM3 visual segmentation over an existing run artifact. It never "
            "renders a new camera view. Provide exactly one text prompt or "
            "single positive point."
        ),
        "returns": """A successful top-ranked mask is projected through the matching world map to produce world_xyz, plus geometry that world_xyz alone cannot carry:

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
  bottle) -- height alone cannot tell these apart.""",
        "when": (
            'Call world_extent(mode="held_object") after a pick and before a '
            "release to get the grasped object's actual offset from the "
            "end-effector; move_to commands the end-effector, not the object, "
            "and the offset is not constant across grasps."
        ),
        "how": (
            "Pass `entity` to register this reading under a name you choose. "
            "Readings are append-only: a later segment of the same entity adds "
            "to its history instead of replacing it, so a motion can always "
            "cite the reading it was planned from. Every subsequent tool "
            "result then carries that entity's latest position and a "
            "stale_reason for it. Re-segment anything whose stale_reason is "
            "not 'fresh' before committing a motion to it, and resolve any "
            "identity_warning before committing a grasp."
        ),
    },
    "back_project": {
        "what": (
            "Back-project a pixel (row, col) to a world XYZ point using the "
            "selected camera's precomputed world map. Row 0 = top of image, "
            "col 0 = left."
        ),
        "returns": "world_xyz in meters.",
        "when": (
            "USE THIS to find where an object is in the world — look at the "
            "high-resolution paths returned by view_driver_state to pick a "
            "pixel on the target object, then call back_project. Use "
            "camera='agentview' for global tabletop layout and object "
            "locations; use camera='wrist' for close-range details near the "
            "gripper, occlusions, and container/cabinet interiors."
        ),
        "how": """The default resolution is high (1024x1024). Pass resolution='low' only for pixels from the embedded/standard 256 image. The pixel coordinates must come from the same camera and resolution requested here. Sample several pixels on the object and median their xy for robustness.
REGION MODE: pass row_range=[r0,r1] and col_range=[c0,c1] instead of row/col
to get the midpoint of world xy over that pixel window, with an optional
world-z band (z_min, z_max). Use it for the center of a container cavity or
flat region, where a single-pixel or mask-median estimate is biased toward an
edge/rim.""",
    },
    "world_extent": {
        "what": (
            "Query occupied space inside a world-frame box, fusing both "
            "cameras. Both world maps already hold WORLD coordinates, so "
            "fusing them is a concatenation with no registration step "
            "(measured agreement on the shared table plane is ~3 mm). This is "
            "read-only and never advances the environment or renders a new "
            "view, the same as back_project."
        ),
        "when": (
            "Use mode='occupancy' to locate a container wall or check "
            "reachable space before a move -- it reports the nearest occupied "
            "surface along each axis from the box centre, which is what a "
            "container's wall position looks like in this representation. Use "
            "mode='held_object' after a pick, before a release, to get the "
            "grasped object's actual offset from the end-effector: move_to "
            "commands the end-effector, not the object, and that offset is not "
            "a fixed constant across grasps."
        ),
    },
    "compare_extent": {
        "what": (
            "Diff the occupied space inside a world-frame box between two "
            "steps. Read-only: never advances the environment and never "
            "renders a new view."
        ),
        "returns": (
            "Voxels are compared as SETS, so added and removed space are "
            "reported separately: a single net count can be zero while "
            "everything inside moved."
        ),
        "when": """Use this to VERIFY that an action did what you intended, without going through segmentation. Every step's world map is already on disk, so "did anything change here" is a geometry question, not a recognition one — it does not depend on SAM3 grounding a noun, and it works when you cannot inspect the images yourself.
What it answers well:
- did the object I released actually land inside the container? Box the
  container's interior and compare the step before the release with the step
  after; look for voxels_added there.
- did the object I meant to pick actually leave the table? Box where it was
  and look for voxels_removed.
- did I disturb something I was not aiming at? Box that thing and check that
  the delta is near zero.""",
        "failure_modes": """⚠ Compare ADJACENT steps, not step 0 against the end. Across a full episode the point count inside one fixed box swung 50x on real runs purely because the wrist camera ended up closer, so the voxel counts tracked how much the cameras saw rather than what was there. Adjacent steps share a viewpoint and the diff is stable.
⚠ Occlusion is the other trap. Space empties either because the object left, or
because the arm now stands between the camera and it, and no diff of two clouds
can separate those. Check n_points_in_box at both steps first: a large drop
there alongside a large voxels_removed is as consistent with a new occlusion as
with a moved object. Treat a removal as evidence only when the point count held
up.
⚠ A change here is NOT task success — those are different claims. On four real
releases the signature was indistinguishable between runs that solved the task
and runs that never terminated: matter arrived in the container box in all
four, because an object perched on the rim registers like a seated one. Only
the environment's own checker establishes success; use this to confirm that
something moved where you intended, then check libero_terminated separately.""",
    },
}


def render_description(name: str) -> str:
    """Render a LIBERO tool's docs entry into its model-facing description."""
    return render_doc(LIBERO_TOOL_DOCS[name])


validate_docs(LIBERO_TOOL_DOCS, "LIBERO_TOOL_DOCS")
