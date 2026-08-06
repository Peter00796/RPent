"""Pure geometry helpers shared by the LIBERO primitives and perception tools.

Nothing here touches the environment, the filesystem, or the agent: these are
array/argument transforms only, so they stay directly unit-testable.

These are internal helpers, not agent tools — never decorate them with ``@tool``.
Doing so replaces the function with a ``StructuredTool`` object, which breaks
every in-process caller (they call these directly, not via ``.invoke()``) and
exposes an argument coercion helper to the planner as if it were a capability.
The agent-facing surface is :mod:`robots.libero.tools.agent_tools`, and nothing
else.
"""
from __future__ import annotations

from typing import Any

import numpy as np


def _normalize_xyz(xyz):
    """Coerce an LLM-supplied xyz into a length-3 list[float]."""
    if not isinstance(xyz, (list, tuple)) or len(xyz) != 3:
        raise ValueError(
            'xyz must be a JSON array of three numbers, e.g. "xyz":[-0.05,0,0.3]'
        )
    return [float(v) for v in xyz]


def _metric_depth(depth: Any, camera_meta: dict) -> np.ndarray:
    d = np.asarray(depth, dtype=np.float32)
    if d.ndim == 3:
        d = d[..., 0]
    near = camera_meta.get("depth_near")
    far = camera_meta.get("depth_far")
    if near is not None and far is not None:
        d = near / (1.0 - d * (1.0 - near / far))
    return d


def _world_from_depth(depth_metric: np.ndarray, camera_meta: dict) -> np.ndarray:
    k_matrix = np.array(camera_meta["intrinsic_K"], dtype=np.float64)
    extrinsic = np.array(camera_meta["extrinsic_cam2world"], dtype=np.float64)
    fx, fy = k_matrix[0, 0], k_matrix[1, 1]
    cx, cy = k_matrix[0, 2], k_matrix[1, 2]
    height, width = depth_metric.shape
    rr, cc = np.mgrid[0:height, 0:width]
    z = depth_metric.astype(np.float64)
    camera_points = np.stack(
        [(cc - cx) * z / fx, (rr - cy) * z / fy, z, np.ones_like(z)],
        axis=-1,
    )
    return (camera_points @ extrinsic.T)[..., :3]


def _mask_to_world(mask: np.ndarray, world_map: np.ndarray,
                   min_valid: int = 10) -> dict:
    if world_map.ndim != 3 or world_map.shape[2] < 3:
        return {
            "world_xyz": None,
            "world_error": f"invalid world map shape: {tuple(world_map.shape)}",
            "n_pixels": int(mask.sum()),
            "n_valid": 0,
            "mask_resized_to_world_shape": False,
        }

    if mask.shape != world_map.shape[:2]:
        return {
            "world_xyz": None,
            "world_error": (
                f"mask/world shape mismatch: mask={tuple(mask.shape)}, "
                f"world={tuple(world_map.shape[:2])}"
            ),
            "n_pixels": int(mask.sum()),
            "n_valid": 0,
            "mask_resized_to_world_shape": False,
        }

    ys, xs = np.where(mask)
    if ys.size == 0:
        return {"world_xyz": None, "world_error": "empty mask"}

    pts = world_map[ys, xs].astype(np.float64)
    valid = np.isfinite(pts).all(axis=1) & (np.abs(pts).sum(axis=1) > 1e-6)
    pts = pts[valid]
    result = {
        "centroid_pixel": [
            int(round(float(np.median(xs)))),
            int(round(float(np.median(ys)))),
        ],
        "n_pixels": int(mask.sum()),
        "n_valid": int(pts.shape[0]),
        "mask_resized_to_world_shape": False,
    }
    if pts.shape[0] < min_valid:
        result.update({
            "world_xyz": None,
            "world_error": f"too few valid depth pixels ({int(pts.shape[0])})",
        })
        return result

    result["world_xyz"] = [
        round(float(np.median(pts[:, 0])), 4),
        round(float(np.median(pts[:, 1])), 4),
        round(float(np.median(pts[:, 2])), 4),
    ]

    # world_xyz is a PER-AXIS median, so for a non-convex mask (an L-shape, a
    # ring, a hollow container) the three medians need not describe any point on
    # the surface. One number also cannot serve grasping, placing-inside and
    # placing-on-top, which want different points. Expose the mask's actual 3D
    # extent so the caller can pick the reduction its task needs.
    z = pts[:, 2]
    z_lo, z_hi = float(z.min()), float(z.max())
    result["bbox_3d"] = {
        "min": [round(float(pts[:, i].min()), 4) for i in range(3)],
        "max": [round(float(pts[:, i].max()), 4) for i in range(3)],
        "extent": [round(float(pts[:, i].max() - pts[:, i].min()), 4)
                   for i in range(3)],
    }
    result["z_profile"] = [round(float(np.percentile(z, p)), 4)
                           for p in (5, 25, 50, 75, 95)]

    # bbox_3d is axis-aligned, so it cannot describe a rotated object: a bottle
    # lying at 45 degrees fills a large box whose extents are all diagonals. Fit
    # the box to the points instead — that recovers the grasp axis.
    shape = _principal_axes(pts, min_valid=min_valid)
    if shape is not None:
        result["shape"] = shape

    # Top ring: for a raised container this is the rim, and its xy centre is the
    # centre of the OPENING. Note a single side camera sees only the near wall
    # and part of the interior, so this estimate is biased away from the camera;
    # it is a bound on the opening centre, not the centre itself.
    top = pts[z >= np.percentile(z, 85)]
    if top.shape[0] >= min_valid:
        # No single reduction of a one-camera cloud recovers a hollow container's
        # true opening centre, so this reports BOUNDS instead of another candidate
        # point. Scored against 23 finished runs of a basket-placement task: the 9
        # releases that succeeded all sat 1.2-9.3 cm on the -x side of world_xyz,
        # while all 14 that failed sat within +-1.3 cm of it. Distance to the
        # successful drop was 4.1 cm for world_xyz, 3.7 cm for the ring mean and
        # 3.9 cm for the range midpoint -- none is the answer, and the range
        # midpoint over-corrects (6.3 cm on the basket measured here). What
        # actually separates success from failure is DIRECTION: stay off the rim
        # edge nearest the camera. camera_near_axis names it.
        x0, x1 = float(top[:, 0].min()), float(top[:, 0].max())
        y0, y1 = float(top[:, 1].min()), float(top[:, 1].max())
        rim = {
            "xy_range": {"x": [round(x0, 4), round(x1, 4)],
                         "y": [round(y0, 4), round(y1, 4)]},
            "xy_span": [round(x1 - x0, 4), round(y1 - y0, 4)],
            "xy_center": [round(float(top[:, 0].mean()), 4),
                          round(float(top[:, 1].mean()), 4)],
            "xy_bbox_center": [round((x0 + x1) / 2.0, 4), round((y0 + y1) / 2.0, 4)],
            "z_mean": round(float(top[:, 2].mean()), 4),
            "n": int(top.shape[0]),
        }
        # Which rim edge faces the camera: that edge is over-represented in the
        # cloud AND is the edge an object bounces off when released too close.
        cam = _camera_origin_world()
        if cam is not None:
            # Which edge faces the camera is set by the DIRECTION from the
            # opening to the camera, not by which coordinate happens to be
            # numerically closer. Comparing |cam - edge| per axis independently
            # can pick the wrong edge when the camera is far along one axis and
            # only slightly offset along the other.
            cx = (x0 + x1) / 2.0
            cy = (y0 + y1) / 2.0
            vx, vy = float(cam[0]) - cx, float(cam[1]) - cy
            if abs(vx) >= abs(vy):
                rim["camera_near_axis"] = "x"
                rim["camera_near_edge"] = round(x1 if vx > 0 else x0, 4)
                rim["retreat_direction"] = "-x" if vx > 0 else "+x"
            else:
                rim["camera_near_axis"] = "y"
                rim["camera_near_edge"] = round(y1 if vy > 0 else y0, 4)
                rim["retreat_direction"] = "-y" if vy > 0 else "+y"
            rim["note"] = (
                "Pick a release xy inside xy_range, at least 0.02 m away from "
                "camera_near_edge along camera_near_axis (i.e. move in "
                "retreat_direction). Clearance either side is about "
                "(xy_span - object_width) / 2.")
        result["rim"] = rim

    # Interior: points well below the top ring but above the table. For a hollow
    # container these are the floor seen through the opening.
    span = z_hi - z_lo
    if span > 0.02:
        inner = pts[(z < z_lo + 0.35 * span) & (z > 0.012)]
        if inner.shape[0] >= min_valid:
            result["interior"] = {
                "xy_median": [round(float(np.median(inner[:, 0])), 4),
                              round(float(np.median(inner[:, 1])), 4)],
                "z_median": round(float(np.median(inner[:, 2])), 4),
                "n": int(inner.shape[0]),
            }
        # A container reads as a high ring ENCLOSING a low middle. Height alone
        # is not enough: an upright bottle also has a high cap above low mask
        # pixels near the table and passes a pure height test. What separates
        # them is containment -- for a basket essentially all interior points
        # fall inside the rim's xy footprint (measured 1.00 on one scene), for a
        # bottle almost none do (measured 0.07 and 0.00) because the cap is a
        # small patch offset from the body below it.
        if "rim" in result and "interior" in result and inner.shape[0] >= min_valid:
            rx0, rx1 = float(top[:, 0].min()), float(top[:, 0].max())
            ry0, ry1 = float(top[:, 1].min()), float(top[:, 1].max())
            enclosed = float(
                ((inner[:, 0] >= rx0) & (inner[:, 0] <= rx1)
                 & (inner[:, 1] >= ry0) & (inner[:, 1] <= ry1)).mean()
            )
            result["interior_enclosed_frac"] = round(enclosed, 3)
            result["looks_hollow"] = bool(
                enclosed > 0.6
                and result["rim"]["z_mean"] - result["interior"]["z_median"] > 0.03
            )
    return result


def _principal_axes(pts: np.ndarray, min_valid: int = 10) -> dict | None:
    """Describe the mask's shape in the object's own frame, not the world's.

    ``bbox_3d`` is axis-aligned, so a object lying at 45 degrees reports three
    large extents that describe nothing: its long axis is a diagonal of that box.
    Principal-component axes recover the object's own frame, which is what a
    grasp needs — the fingers must close across the SHORT horizontal extent, and
    that direction is only visible once the box is rotated to fit the points.

    The wrist is commanded about world z, so the useful reduction is not the 3D
    principal axis (for an upright bottle that is vertical, and its horizontal
    projection is meaningless) but a 2D fit to the xy FOOTPRINT. Reported as an
    axis, not a direction: an eigenvector's sign is arbitrary, so the yaw is
    normalised to [-90, 90) degrees and a grasp is equally valid either way along
    it.

    Deliberately does not emit a ``target_yaw``. Which eef axis the fingers close
    along is gripper geometry, and a wrong 90 degrees there would rotate every
    grasp orthogonal to correct while looking perfectly reasonable. This reports
    the object; mapping its axes onto ``rotate_wrist`` is a one-time measurement
    for a given gripper, and being a hardware invariant it belongs in memory
    rather than being re-derived per run.

    Bias: these are points from one camera's surface sample, so the far side is
    unseen and every extent is a LOWER bound on the object's true size.
    """
    if pts.shape[0] < min_valid:
        return None

    # Trim the farthest 1% from the mask's 3D median before fitting. A mask's
    # boundary pixels straddle the object edge, and their depth bleeds onto
    # whatever is behind, so a handful of points land metres away — measured on 14
    # real readings, untrimmed min-max extents were inflated up to 6x (a soup can
    # read as 0.40 m across, a bottle as 0.24 m). One percent is enough because
    # those points are very few and very extreme: at 1% the same can reads 0.067 m
    # and going to 5% moves it only 0.003 m further, while legitimate geometry
    # barely moves (a real 0.142 m bottle loses 2 mm). The task prompt warns about
    # the same effect for hand-picked pixels; a fitted box has to defend itself.
    distances = np.linalg.norm(pts - np.median(pts, axis=0), axis=1)
    kept = pts[distances <= np.percentile(distances, 99.0)]
    n_trimmed = int(pts.shape[0] - kept.shape[0])
    if kept.shape[0] < min_valid:
        return None
    pts = kept

    xy = pts[:, :2]
    centre = xy.mean(axis=0)
    centred = xy - centre
    try:
        _, eigenvectors = np.linalg.eigh(np.cov(centred.T))
    except np.linalg.LinAlgError:
        return None
    # Order the two axes by the extent actually REPORTED, not by variance. The
    # higher-variance axis is not always the one with the wider min-max range —
    # variance follows the bulk, range follows the tails — and when they disagreed
    # the reply labelled the narrow axis "long", so graspable_width_m came out as
    # the larger number and told the planner a 6 cm bottle needed a 24 cm span.
    measured = []
    for vec in (eigenvectors[:, -1], eigenvectors[:, 0]):
        projection = centred @ vec
        measured.append(
            (float(projection.max() - projection.min()), float(np.std(projection)), vec)
        )
    measured.sort(key=lambda item: -item[0])
    (long_extent, long_std, long_vec), (short_extent, short_std, short_vec) = measured
    if long_extent <= 1e-6:
        return None

    def _axis_yaw(vec) -> float:
        """Yaw of an undirected axis, folded into [-90, 90) degrees."""
        angle = float(np.degrees(np.arctan2(float(vec[1]), float(vec[0]))))
        while angle >= 90.0:
            angle -= 180.0
        while angle < -90.0:
            angle += 180.0
        return round(angle, 1)

    # Shape RATIOS come from the projections' standard deviations, not from the
    # min-max extents. A square footprint's fitted axes land on its diagonals, so
    # its min-max range overstates the side by up to sqrt(2) — enough to make a
    # cube read as "lying". The covariance of a square is isotropic, so its
    # spreads are equal whatever the rotation, which is the property the ratio
    # tests need. Min-max is still what gets REPORTED, because a gripper has to
    # span the full width, not one standard deviation.
    spread_long = max(long_std, short_std)
    spread_short = min(long_std, short_std)
    spread_z = float(np.std(pts[:, 2]))
    aspect = spread_short / spread_long if spread_long > 1e-9 else 1.0
    # Below roughly 1.2:1 the footprint is round enough that the fitted axis is
    # set by sampling noise, not by the object. Saying so stops the planner
    # rotating the wrist to a number that means nothing for a bowl or a can.
    meaningful = aspect < 0.83

    height = float(pts[:, 2].max() - pts[:, 2].min())
    try:
        thickness = float(
            np.sqrt(max(float(np.linalg.eigvalsh(np.cov(pts.T))[0]), 0.0)) * 4.0
        )
    except np.linalg.LinAlgError:
        thickness = float("nan")

    if spread_z > 1.3 * spread_long:
        orientation = "upright"
    elif spread_long > 1.3 * spread_z:
        orientation = "lying"
    else:
        orientation = "ambiguous"

    return {
        "footprint": {
            "long_axis_yaw_deg": _axis_yaw(long_vec),
            "short_axis_yaw_deg": _axis_yaw(short_vec),
            "long_extent_m": round(long_extent, 4),
            "short_extent_m": round(short_extent, 4),
            "aspect_short_over_long": round(aspect, 3),
            "yaw_is_meaningful": bool(meaningful),
            "xy_center": [round(float(centre[0]), 4), round(float(centre[1]), 4)],
        },
        "height_m": round(height, 4),
        "orientation": orientation,
        "planar": bool(np.isfinite(thickness) and thickness < 0.006),
        "graspable_width_m": round(short_extent, 4),
        "n": int(pts.shape[0]),
        "n_outliers_trimmed": n_trimmed,
        "note": (
            "Axes fitted to the xy footprint, in the object's own frame. The "
            "gripper must close ACROSS the short axis, spanning graspable_width_m "
            "(= short_extent_m); the direction it travels is short_axis_yaw_deg. "
            "Yaw is an AXIS folded into [-90, 90): a grasp is equally valid "
            "either way along it. This is object geometry, NOT a rotate_wrist "
            "argument — which eef axis the fingers close along is gripper "
            "geometry, so verify that mapping once and reuse it. When "
            "yaw_is_meaningful is false the footprint is near-round and any yaw "
            "is as good as another. Extents come from one camera's surface "
            "sample with the farthest 1% of points trimmed (mask edges bleed "
            "onto the background behind), so each is a LOWER bound on the true "
            "size."
        ),
    }


def _camera_origin_world() -> np.ndarray | None:
    """World-frame position of the static agentview camera, or None.

    Read from the run's camera_meta.json: the translation column of
    extrinsic_cam2world is the camera origin. Used only to decide which rim edge
    faces the camera -- the edge that is over-represented in a one-camera cloud
    and the edge an object bounces off when released too close to it.
    """
    import json

    from robots.libero.tools.artifacts import artifact_path
    from rpent.utils.logging import get_output_dir

    try:
        p = artifact_path(get_output_dir(), "metadata", camera="agentview",
                          resolution="low")
        if not p.exists():
            return None
        meta = json.loads(p.read_text())
        ext = np.asarray(meta["extrinsic_cam2world"], dtype=np.float64)
        return ext[:3, 3]
    except Exception:
        return None


def _step_cloud(nn: int, cameras: str) -> tuple[np.ndarray | None, list[str], list[str]]:
    """Load and fuse one step's world map(s). Returns ``(points, used, missing)``.

    Both maps already hold WORLD coordinates -- each camera's intrinsics and
    cam2world extrinsic were applied when the map was written -- so fusing them is
    a concatenation with no registration step.
    """
    from robots.libero.tools.artifacts import artifact_path
    from rpent.utils.logging import get_output_dir

    wanted = ("agentview", "wrist") if cameras == "fused" else (cameras,)
    clouds: list[np.ndarray] = []
    used: list[str] = []
    missing: list[str] = []
    for cam in wanted:
        loaded = False
        for res in ("high", "low"):
            try:
                arr = np.load(
                    artifact_path(get_output_dir(), "world", step=nn, camera=cam,
                                  resolution=res)
                )
            except Exception:
                continue
            pts = arr.reshape(-1, arr.shape[2]).astype(np.float64)[:, :3]
            pts = pts[np.isfinite(pts).all(axis=1) & (np.abs(pts).sum(axis=1) > 1e-6)]
            if pts.shape[0]:
                clouds.append(pts)
                used.append(f"{cam}:{res}")
                loaded = True
            break
        if not loaded:
            missing.append(cam)
    if not clouds:
        return None, used, missing
    return np.vstack(clouds), used, missing


def _step_eef(nn: int) -> np.ndarray | None:
    """End-effector position recorded at step ``nn``, or None."""
    from robots.libero.tools.state import _load_step

    try:
        state = _load_step(nn).get("state") or {}
    except Exception:
        return None
    eef = state.get("robot0_eef_pos")
    if eef is None or len(eef) < 3:
        return None
    return np.asarray(eef, dtype=np.float64)[:3]


def compare_extent(
    x_range: list | None = None,
    y_range: list | None = None,
    z_range: list | None = None,
    step_a: int | None = None,
    step_b: int | None = None,
    cameras: str = "fused",
    voxel: float = 0.01,
    exclude_arm_radius: float = 0.12,
) -> dict:
    """Diff the occupied space inside a world-frame box between two steps.

    Answers "did that action change anything here" without going through
    segmentation. Every step's world map is on disk, so the question is geometry,
    not recognition -- which matters because it makes verification independent of
    the one channel that can fail to ground a noun.

    Voxels are compared as sets, so the reply separates space that became
    occupied from space that emptied, rather than reporting a single count that
    could net to zero while everything moved.

    ⚠ Occlusion is the trap. Points vanish from a box either because the object
    left or because the arm moved between the camera and it, and no diff of two
    clouds can tell those apart. ``n_points_in_box`` is reported per step for
    exactly this reason: a large drop in total points alongside a large
    ``voxels_removed`` is as consistent with a new occlusion as with a moved
    object. Treat a removal as evidence only when the point count held up.

    ⚠ Compare ADJACENT steps, not the whole episode. Measured over six real runs:
    across a full episode the point count inside one fixed box swung by 50x purely
    because the wrist camera ended up closer, so the voxel counts tracked how much
    the cameras happened to see rather than what was physically there, and the net
    change did not even agree in sign with the outcome. Between adjacent steps the
    viewpoint barely moves and the diff is stable (four releases all read +78..+146
    voxels added against 3..14 removed).

    ⚠ This measures a world-state change, not task success — they are different
    claims. On those same four releases the signature was indistinguishable
    between the two runs that solved the task and the two that never terminated:
    matter arrived inside the container box in all four. An object perched on the
    rim registers like a seated one. Only the environment's own checker can
    establish success.
    """
    from rpent.utils.logging import get_output_dir
    from robots.libero.tools.state import _latest_step

    if cameras not in ("fused", "agentview", "wrist"):
        return {"error": f"bad cameras '{cameras}' (use 'fused', 'agentview' or 'wrist')"}
    try:
        voxel = float(voxel)
    except Exception:
        return {"error": "voxel must be a number, in metres"}
    if not 0.002 <= voxel <= 0.05:
        return {"error": f"voxel {voxel} out of range (use 0.002 .. 0.05 m)"}

    latest = _latest_step()
    if latest is None:
        return {"error": "no world-map files available"}
    nb = latest if step_b is None else int(step_b)
    na = 0 if step_a is None else int(step_a)
    if na == nb:
        return {"error": f"step_a and step_b are both {na}; pick two different steps"}

    def _rng(r, lo, hi):
        if r is None:
            return lo, hi
        try:
            a, b = float(r[0]), float(r[1])
        except Exception:
            return None
        return min(a, b), max(a, b)

    bounds = []
    for r, lo, hi in ((x_range, -1.0, 1.0), (y_range, -1.0, 1.0),
                      (z_range, 0.012, 1.0)):
        got = _rng(r, lo, hi)
        if got is None:
            return {"error": "x_range/y_range/z_range must each be [min, max] numbers"}
        bounds.append(got)
    (x0, x1), (y0, y1), (z0, z1) = bounds

    sides: dict[int, dict[str, Any]] = {}
    keysets: dict[int, set] = {}
    for nn in (na, nb):
        pts, used, missing = _step_cloud(nn, cameras)
        if pts is None:
            return {"error": f"no world map loadable for step {nn} (missing: {missing})"}
        eef = _step_eef(nn)
        n_arm = 0
        if eef is not None and exclude_arm_radius and exclude_arm_radius > 0:
            keep = np.linalg.norm(pts - eef, axis=1) > float(exclude_arm_radius)
            n_arm = int((~keep).sum())
            pts = pts[keep]
        pts = pts[pts[:, 2] > 0.012]
        inside = pts[
            (pts[:, 0] >= x0) & (pts[:, 0] <= x1)
            & (pts[:, 1] >= y0) & (pts[:, 1] <= y1)
            & (pts[:, 2] >= z0) & (pts[:, 2] <= z1)
        ]
        keys = (
            set(map(tuple, np.unique(np.floor(inside / voxel).astype(np.int64), axis=0)))
            if inside.shape[0]
            else set()
        )
        keysets[nn] = keys
        side = {
            "cameras_used": used,
            "eef_pos": [round(float(v), 4) for v in eef] if eef is not None else None,
            "arm_points_removed": n_arm,
            "n_points_in_box": int(inside.shape[0]),
            "occupied_voxels": len(keys),
        }
        if inside.shape[0]:
            side["centroid"] = [round(float(inside[:, i].mean()), 4) for i in range(3)]
            side["z_range"] = [round(float(inside[:, 2].min()), 4),
                               round(float(inside[:, 2].max()), 4)]
        sides[nn] = side

    ka, kb = keysets[na], keysets[nb]
    added, removed, common = kb - ka, ka - kb, ka & kb
    union = ka | kb
    result: dict[str, Any] = {
        "box": {"x": [round(x0, 4), round(x1, 4)], "y": [round(y0, 4), round(y1, 4)],
                "z": [round(z0, 4), round(z1, 4)]},
        "voxel_m": voxel,
        f"step_{na}": sides[na],
        f"step_{nb}": sides[nb],
        "step_a": na,
        "step_b": nb,
        "delta": {
            "voxels_added": len(added),
            "voxels_removed": len(removed),
            "voxels_unchanged": len(common),
            "occupied_voxels_net": len(kb) - len(ka),
            "iou": round(len(common) / len(union), 3) if union else None,
        },
    }
    ca, cb = sides[na].get("centroid"), sides[nb].get("centroid")
    if ca and cb:
        shift = np.asarray(cb) - np.asarray(ca)
        result["delta"]["centroid_shift"] = [round(float(v), 4) for v in shift]
        result["delta"]["centroid_shift_m"] = round(float(np.linalg.norm(shift)), 4)
    if added:
        pts_added = np.asarray(sorted(added), dtype=np.float64) * voxel + voxel / 2.0
        result["delta"]["added_centroid"] = [round(float(pts_added[:, i].mean()), 4)
                                            for i in range(3)]
    if removed:
        pts_removed = np.asarray(sorted(removed), dtype=np.float64) * voxel + voxel / 2.0
        result["delta"]["removed_centroid"] = [round(float(pts_removed[:, i].mean()), 4)
                                              for i in range(3)]
    drop = sides[na]["n_points_in_box"] - sides[nb]["n_points_in_box"]
    result["caveat"] = (
        "Voxels can empty because the object left OR because the arm now occludes "
        "the view; a cloud diff cannot separate those. Compare n_points_in_box "
        f"across the two steps first (here: {sides[na]['n_points_in_box']} -> "
        f"{sides[nb]['n_points_in_box']}, change {-drop:+d}). Trust "
        "voxels_removed only when the point count held up. Points are one "
        "camera's surface sample, so an object hidden behind another is absent "
        "from both steps and invisible to this diff."
    )
    result["output_dir"] = str(get_output_dir())
    return result


def world_extent(
    x_range: list | None = None,
    y_range: list | None = None,
    z_range: list | None = None,
    step: int | None = None,
    cameras: str = "fused",
    voxel: float = 0.01,
    exclude_arm_radius: float = 0.12,
    mode: str = "occupancy",
) -> dict:
    """Query occupied space inside a world-frame box, fusing both cameras.

    Both world maps already hold WORLD coordinates -- each camera's own
    intrinsics and cam2world extrinsic were applied when the map was written --
    so fusing them is a concatenation with no registration step. Measured
    agreement on the shared table plane is ~3 mm.

    The manipulator appears in both clouds (18% of wrist points sit within 10 cm
    of the eef at close range), so a naive map reports the robot's own body as an
    obstacle. Points within ``exclude_arm_radius`` of the current eef are dropped.
    """
    from robots.libero.tools.artifacts import artifact_path
    from rpent.utils.logging import get_output_dir
    from robots.libero.tools.state import _latest_step, _load_step

    if mode not in ("occupancy", "held_object"):
        return {"error": f"bad mode '{mode}' (use 'occupancy' or 'held_object')"}
    if cameras not in ("fused", "agentview", "wrist"):
        return {"error": f"bad cameras '{cameras}' (use 'fused', 'agentview' or 'wrist')"}
    try:
        voxel = float(voxel)
    except Exception:
        return {"error": "voxel must be a number, in metres"}
    if not 0.002 <= voxel <= 0.05:
        return {"error": f"voxel {voxel} out of range (use 0.002 .. 0.05 m)"}

    latest = _latest_step()
    nn = latest if step is None else int(step)
    if nn is None:
        return {"error": "no world-map files available"}
    try:
        data = _load_step(nn)
    except Exception as e:
        return {"error": f"step {nn} not present in state trace: {e}"}

    wanted = ("agentview", "wrist") if cameras == "fused" else (cameras,)
    clouds, used, missing = [], [], []
    for cam in wanted:
        loaded = False
        for res in ("high", "low"):
            try:
                p = artifact_path(get_output_dir(), "world", step=nn,
                                  camera=cam, resolution=res)
                arr = np.load(p)
            except Exception:
                continue
            pts = arr.reshape(-1, arr.shape[2]).astype(np.float64)[:, :3]
            pts = pts[np.isfinite(pts).all(axis=1) & (np.abs(pts).sum(axis=1) > 1e-6)]
            if pts.shape[0]:
                clouds.append(pts)
                used.append(f"{cam}:{res}")
                loaded = True
            break
        if not loaded:
            missing.append(cam)
    if not clouds:
        return {"error": f"no world map loadable for step {nn} (missing: {missing})"}
    pts = np.vstack(clouds)

    eef = None
    grip_w = None
    state = data.get("state") if isinstance(data, dict) else None
    if isinstance(state, dict):
        e = state.get("robot0_eef_pos")
        if e is not None and len(e) >= 3:
            eef = np.asarray(e, dtype=np.float64)[:3]
        q = state.get("robot0_gripper_qpos")
        if q is not None and len(q) >= 2:
            grip_w = abs(float(q[0])) + abs(float(q[1]))

    if mode == "held_object":
        # move_to commands the END-EFFECTOR, but a task predicate is about where
        # the OBJECT lands, and a grasped object does not sit on the eef axis.
        # Measured on four runs of the same scene: the same bottle sat 1.8, 2.4,
        # 2.7 and 2.9 cm along +x of the eef -- the same grasp width every time,
        # yet a different offset, so no constant can be right. Both cameras
        # agree to a millimetre, and with the gripper OPEN this window reads ~0,
        # which is how we know it is the object and not gripper geometry.
        if eef is None:
            return {"error": "no eef pose recorded for step %d" % nn}
        if grip_w is not None and grip_w > 0.06:
            return {"step": nn, "mode": "held_object", "holding": False,
                    "gripper_width": round(grip_w, 4),
                    "eef_pos": [round(float(v), 4) for v in eef],
                    "note": ("gripper is open (width %.4f) -- nothing held, so "
                             "there is no offset to apply" % grip_w)}
        d_xy = np.linalg.norm(pts[:, :2] - eef[:2], axis=1)
        m = ((pts[:, 2] < eef[2] - 0.02) & (pts[:, 2] > eef[2] - 0.20)
             & (d_xy < 0.06) & (pts[:, 2] > 0.012))
        held = pts[m]
        out = {"step": nn, "mode": "held_object", "cameras_used": used,
               "gripper_width": round(grip_w, 4) if grip_w is not None else None,
               "eef_pos": [round(float(v), 4) for v in eef],
               "n_points": int(held.shape[0])}
        if held.shape[0] < 30:
            out["holding"] = False
            out["note"] = ("only %d points hang below the eef -- either nothing "
                           "is held or the object is occluded from both cameras"
                           % int(held.shape[0]))
            return out
        # The candidate window is a cylinder 2-20 cm below the eef, so when the eef
        # is low it necessarily swallows the table, and the "held object" becomes a
        # slab of tabletop. Measured over 25 closed-gripper steps in 6 real runs,
        # 12 readings were of a surface rather than an object. Three geometric
        # facts separate them, and they separated every case cleanly here: a real
        # grasp measured 3-6 cm across and 9-18 cm tall, while the false ones were
        # 12 cm across (the full window), or 1 cm thick and 7 cm wide (a stove
        # top), or reached the window's own floor clamp.
        xy_extent = float(max(np.ptp(held[:, 0]), np.ptp(held[:, 1])))
        z_extent = float(np.ptp(held[:, 2]))
        bottom = float(held[:, 2].min())
        reasons = []
        if z_extent < 0.012 and xy_extent > 0.04:
            reasons.append(
                f"only {z_extent:.3f} m thick over {xy_extent:.3f} m — a surface, "
                "not a body"
            )
        if bottom <= 0.0125:
            reasons.append(
                "reaches the window's floor clamp, so the window included the table"
            )
        out["xy_extent_m"] = round(xy_extent, 4)
        out["z_extent_m"] = round(z_extent, 4)
        # Reported, not acted on. A blob wider than the gripper's span is suspect,
        # but on the 25 real readings this fired inconsistently on marginal cases
        # and there is no ground truth here for which steps were truly holding —
        # so it warns instead of overriding. Falsely reporting "not holding" is
        # its own harm.
        if xy_extent > 0.09:
            out["shape_warning"] = (
                f"these points span {xy_extent:.3f} m across, wider than the "
                "gripper can hold — they may include the container or the table "
                "rather than only the grasped object, so treat the offset as "
                "approximate and cross-check it after the next move"
            )
        if reasons:
            out["holding"] = False
            out["object_z_range"] = [round(bottom, 4), round(float(held[:, 2].max()), 4)]
            out["note"] = (
                "the points below the eef are geometry, not a grasped object: "
                + "; ".join(reasons)
                + ". Gripper width alone cannot tell these apart — it read the "
                "same on steps that were holding and steps that were not."
            )
            return out

        cen = held.mean(axis=0)
        out["holding"] = True
        out["object_centroid"] = [round(float(v), 4) for v in cen]
        out["offset_from_eef"] = [round(float(cen[0] - eef[0]), 4),
                                  round(float(cen[1] - eef[1]), 4)]
        out["object_z_range"] = [round(float(held[:, 2].min()), 4),
                                 round(float(held[:, 2].max()), 4)]
        out["how_to_use"] = ("To land the object at target xy, command move_to "
                             "at (target_x - offset_from_eef[0], target_y - "
                             "offset_from_eef[1]). Re-query after any re-grasp: "
                             "the offset changes every grasp.")
        return out

    n_before = int(pts.shape[0])
    n_arm = 0
    if eef is not None and exclude_arm_radius and exclude_arm_radius > 0:
        keep = np.linalg.norm(pts - eef, axis=1) > float(exclude_arm_radius)
        n_arm = int((~keep).sum())
        pts = pts[keep]

    # The table plane is not an obstacle for reasoning about reachable space.
    pts = pts[pts[:, 2] > 0.012]

    def _rng(r, lo, hi):
        if r is None:
            return lo, hi
        try:
            a, b = float(r[0]), float(r[1])
        except Exception:
            return None
        return min(a, b), max(a, b)

    bounds = []
    for r, lo, hi in ((x_range, -1.0, 1.0), (y_range, -1.0, 1.0), (z_range, 0.012, 1.0)):
        got = _rng(r, lo, hi)
        if got is None:
            return {"error": "x_range/y_range/z_range must each be [min, max] numbers"}
        bounds.append(got)
    (x0, x1), (y0, y1), (z0, z1) = bounds

    m = ((pts[:, 0] >= x0) & (pts[:, 0] <= x1)
         & (pts[:, 1] >= y0) & (pts[:, 1] <= y1)
         & (pts[:, 2] >= z0) & (pts[:, 2] <= z1))
    box = pts[m]
    result = {
        "step": nn,
        "cameras_used": used,
        "cameras_missing": missing,
        "voxel_m": voxel,
        "box": {"x": [round(x0, 4), round(x1, 4)],
                "y": [round(y0, 4), round(y1, 4)],
                "z": [round(z0, 4), round(z1, 4)]},
        "eef_pos": [round(float(v), 4) for v in eef] if eef is not None else None,
        "arm_points_removed": n_arm,
        "n_points_total": n_before,
        "n_points_in_box": int(box.shape[0]),
    }
    if box.shape[0] < 8:
        result["occupied_voxels"] = 0
        result["note"] = ("box is empty of geometry above the table -- either free "
                          "space, or outside the cameras' field of view")
        return result

    keys = np.floor(box / voxel).astype(np.int64)
    uniq = np.unique(keys, axis=0)
    result["occupied_voxels"] = int(uniq.shape[0])
    result["extent"] = {
        "min": [round(float(box[:, i].min()), 4) for i in range(3)],
        "max": [round(float(box[:, i].max()), 4) for i in range(3)],
    }
    result["z_profile"] = [round(float(np.percentile(box[:, 2], p)), 4)
                           for p in (5, 25, 50, 75, 95)]

    # Nearest occupied surface along each axis from the box centre. This is
    # what locates a container wall.
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    walls = {}
    band = max(voxel * 3, 0.02)
    for axis, name, c, other_c, oa in ((0, "x", cx, cy, 1), (1, "y", cy, cx, 0)):
        near = box[np.abs(box[:, oa] - other_c) <= band]
        if near.shape[0] < 8:
            continue
        lower = near[near[:, axis] < c]
        upper = near[near[:, axis] > c]
        walls[f"-{name}"] = (round(float(lower[:, axis].max()), 4)
                             if lower.shape[0] else None)
        walls[f"+{name}"] = (round(float(upper[:, axis].min()), 4)
                             if upper.shape[0] else None)
    result["nearest_surface_from_box_center"] = walls
    result["caveat"] = ("Static scene geometry only. It does NOT predict OSC "
                        "undershoot or a pose broken by rotate_wrist -- on the "
                        "one run measured, occupancy explained 1 of 3 stalled "
                        "moves. Fusion gain also depends on eef height: +46% "
                        "occupied voxels at eef z=0.29, +2% at z=0.075, because "
                        "the gripper occludes the wrist view at close range.")
    return result
