"""Read-only perception tools: SAM3 segmentation, calibration, back-projection.

None of these advance the environment — they read artifacts already dumped by
:mod:`robots.libero.tools.state`. ``segment`` needs the primitives-owned SAM3
client, so it ships as :class:`SegmentMixin`; ``view_camera_meta`` and
``back_project`` are stateless module functions.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import imageio.v2 as imageio
import numpy as np

from rpent.utils.logging import get_output_dir

from robots.libero.tools.artifacts import artifact_path
from robots.libero.tools.geometry import _mask_to_world
from robots.libero.tools.state import (
    _latest_step,
    _load_camera_meta,
    _load_depth,
    _load_step,
)

if TYPE_CHECKING:
    from rpent.utils.sam3_client import Sam3Client


class SegmentMixin:
    """The ``segment`` tool. Requires the :class:`LiberoPrimitives` core."""

    # Provided by LiberoPrimitives (annotations only — no runtime attributes).
    _sam3_client: Sam3Client

    def segment(
        self,
        prompt: str = "",
        camera: str = "agentview",
        step: int | None = None,
        point: list[int] | None = None,
        min_score: float = 0.2,
    ) -> dict:
        """Call SAM3 on an existing image artifact without advancing the env.

        This tool deliberately does not render camera views or create wrist/high-res
        artifacts. Errors are structured so the agent can continue with image
        inspection and ``back_project``.
        """
        nn = _latest_step() if step is None else int(step)
        if nn is None:
            return {"error": "no state entries; cannot select segment image"}

        camera = camera or "agentview"
        prompt = prompt.strip()
        has_prompt = bool(prompt)
        has_point = point is not None
        if has_prompt == has_point:
            return {"error": "segment needs exactly one of prompt or point"}
        try:
            image_path, world_path, artifact_pairs = _select_segment_artifacts(
                nn, camera
            )
        except ValueError as e:
            return {"error": str(e)}
        if image_path is None:
            return {
                "error": "complete segment artifacts not found",
                "step": nn,
                "camera": camera,
                "checked_paths": [
                    str(path)
                    for image, world in artifact_pairs
                    for path in (image, world)
                ],
            }

        try:
            data = self._sam3_client.segment(
                image_path,
                text_prompt=prompt if has_prompt else None,
                point=point,
                min_score=min_score,
            )
        except ValueError as e:
            return {
                "error": str(e),
                "step": nn,
                "camera": camera,
                "image_path": str(image_path),
            }
        except Exception as e:
            return {
                "error": f"segmentation service call failed: {e}",
                "step": nn,
                "camera": camera,
                "image_path": str(image_path),
                "fallback": "Use manual visual localization and back_project.",
            }

        out_dir = get_output_dir()
        segment_path, overlay_candidate_path, segment_index = (
            _next_segment_artifact_paths(out_dir, nn)
        )
        overlay_path = None
        mask = data.mask
        if data.found and isinstance(mask, np.ndarray):
            if world_path is None or not world_path.exists():
                world_result = {
                    "world_xyz": None,
                    "world_error": "world map artifact not found for selected image",
                    "expected_world_path": str(world_path) if world_path else None,
                }
            else:
                world_result = _mask_to_world(mask, np.load(world_path))
                world_result["world_path"] = str(world_path)
            overlay_path = overlay_candidate_path
            if not _write_segment_overlay(image_path, mask, overlay_path):
                overlay_path = None
        else:
            world_result = {
                "world_xyz": None,
                "world_error": data.reason or "segmentation did not find a mask",
            }

        segment_blob = {
            "found": data.found,
            "mode": "text" if has_prompt else "point",
            "camera": camera,
            "source_step": nn,
            "segment_index": segment_index,
            "image_path": str(image_path),
            "min_score": min_score,
            "score": round(float(data.score), 3) if data.score is not None else None,
            "box": data.box,
            "mask_shape": list(data.mask_shape) if data.mask_shape else None,
        }
        if has_prompt:
            segment_blob["prompt"] = prompt
        else:
            segment_blob["point"] = point
        if not data.found:
            segment_blob["error"] = data.reason or "SAM3 found no mask"
        segment_blob.update(world_result)
        segment_path.write_text(json.dumps(segment_blob, indent=2, default=str))

        result = {
            "found": data.found,
            "step": nn,
            "camera": camera,
            "image_path": str(image_path),
            "segment_path": str(segment_path),
            "score": segment_blob["score"],
            "box": segment_blob["box"],
            "world_xyz": segment_blob["world_xyz"],
            "world_error": segment_blob.get("world_error"),
        }
        if "error" in segment_blob:
            result["error"] = segment_blob["error"]
            result["fallback"] = "Use manual visual localization and back_project."
        if overlay_path is not None and overlay_path.exists():
            result["overlay_path"] = str(overlay_path)
        return result


def _select_segment_artifacts(nn: int, camera: str):
    out_dir = get_output_dir()
    if camera not in ("agentview", "wrist"):
        raise ValueError(f"unknown segment camera: {camera}")
    pairs = [
        (
            artifact_path(out_dir, "image", step=nn, camera=camera, resolution=resolution),
            artifact_path(out_dir, "world", step=nn, camera=camera, resolution=resolution),
        )
        for resolution in ("high", "low")
    ]

    for image_path, world_path in pairs:
        if image_path.exists() and world_path.exists():
            return image_path, world_path, pairs
    return None, None, pairs


def _next_segment_artifact_paths(out_dir: Path, nn: int):
    segments_dir = artifact_path(out_dir, "segments")
    segments_dir.mkdir(parents=True, exist_ok=True)
    idx = 0
    while True:
        segment_path = segments_dir / f"segment_{nn:02d}_{idx:02d}.json"
        overlay_path = segments_dir / f"segment_overlay_{nn:02d}_{idx:02d}.png"
        if not segment_path.exists() and not overlay_path.exists():
            return segment_path, overlay_path, idx
        idx += 1


def _write_segment_overlay(image_path: Path, mask: np.ndarray,
                           overlay_path: Path) -> bool:
    try:
        image = imageio.imread(image_path)
        if image.ndim != 3 or image.shape[:2] != mask.shape:
            return False
        overlay = image.copy()
        red = np.zeros_like(overlay)
        red[..., 0] = 255
        overlay[mask] = (
            0.55 * overlay[mask].astype(np.float32)
            + 0.45 * red[mask].astype(np.float32)
        ).astype(np.uint8)
        imageio.imwrite(overlay_path, overlay)
        return overlay_path.exists()
    except Exception:
        return False


def view_camera_meta(camera: str = "agentview", step: int | None = None) -> dict:
    """Read camera calibration metadata for localization."""
    if camera not in ("agentview", "wrist"):
        return {"error": f"bad camera '{camera}' (use 'agentview' or 'wrist')"}

    nn = None
    if camera == "wrist":
        nn = _latest_step() if step is None else int(step)
        if nn is None:
            return {"error": "no wrist metadata available"}

    try:
        meta = _load_camera_meta(camera, nn)
    except Exception as e:
        return {"error": f"{camera} camera metadata not found: {e}"}

    if camera == "agentview":
        return {"camera": "agentview", "camera_meta": meta}
    return {"camera": "wrist", "step": nn, "camera_meta": meta}


def back_project(
    row: int | None = None,
    col: int | None = None,
    step: int | None = None,
    camera: str = "agentview",
    resolution: str = "high",
    row_range: list | None = None,
    col_range: list | None = None,
    z_min: float | None = None,
    z_max: float | None = None,
) -> dict:
    """Look up a pixel's world XYZ in the precomputed world map."""
    if camera not in ("agentview", "wrist"):
        return {"error": f"bad camera '{camera}' (use 'agentview' or 'wrist')"}
    if resolution not in ("high", "low"):
        return {"error": f"bad resolution '{resolution}' (use 'high' or 'low')"}

    region_mode = row_range is not None or col_range is not None
    if not region_mode and (row is None or col is None):
        return {
            "error": (
                "provide either (row, col) for a single pixel, or "
                "row_range=[r0,r1] and col_range=[c0,c1] for a region center"
            )
        }

    latest = _latest_step()
    nn = latest if step is None else int(step)
    if nn is None:
        return {"error": "no depth/world-map files available"}

    try:
        data = _load_step(nn)
    except Exception as e:
        return {"error": f"step {nn} not present in state trace: {e}"}

    if camera == "agentview":
        hi_artifact = data.get("world_map_hi")
        low_artifact = data.get("world_map")
    else:
        hi_artifact = data.get("wrist_world_map_hi")
        low_artifact = data.get("wrist_world_map")
    source_artifact = hi_artifact if resolution == "high" else low_artifact
    if not source_artifact:
        return {
            "error": (
                f"{camera} {resolution}-resolution world map not recorded "
                f"for step {nn}"
            )
        }

    try:
        world_path = artifact_path(get_output_dir(), "world", step=nn, camera=camera, resolution=resolution)
        world_map = np.load(world_path)
    except Exception as e:
        return {
            "error": (
                f"{camera} {resolution}-resolution artifact not found "
                f"for step {nn}: {e}"
            )
        }

    height, width = world_map.shape[:2]

    if region_mode:
        if row_range is None or col_range is None:
            return {
                "error": "region mode needs BOTH row_range=[r0,r1] and col_range=[c0,c1]"
            }
        try:
            r0, r1 = int(row_range[0]), int(row_range[1])
            c0, c1 = int(col_range[0]), int(col_range[1])
        except Exception:
            return {"error": "row_range/col_range must each be [min, max] integers"}
        r0, r1 = sorted((max(0, r0), min(height, r1)))
        c0, c1 = sorted((max(0, c0), min(width, c1)))
        if r1 <= r0 or c1 <= c0:
            return {
                "error": (
                    f"empty region after clamping to image {height}x{width}: "
                    f"rows [{r0},{r1}] cols [{c0},{c1}]"
                )
            }
        window = world_map[r0:r1, c0:c1].reshape(-1, world_map.shape[2]).astype(
            np.float64
        )
        finite = np.isfinite(window).all(axis=1) & (
            np.abs(window[:, :3]).sum(axis=1) > 1e-6
        )
        pts = window[finite]
        n_total = int(pts.shape[0])
        if z_min is not None:
            pts = pts[pts[:, 2] >= float(z_min)]
        if z_max is not None:
            pts = pts[pts[:, 2] <= float(z_max)]
        if pts.shape[0] < 8:
            return {
                "error": (
                    f"too few valid pixels in region after z-filter "
                    f"({int(pts.shape[0])}); widen the window or the z band"
                ),
                "n_valid_before_zfilter": n_total,
            }
        xs, ys, zs = pts[:, 0], pts[:, 1], pts[:, 2]
        center = [
            round(float((xs.min() + xs.max()) / 2.0), 4),
            round(float((ys.min() + ys.max()) / 2.0), 4),
            round(float(np.median(zs)), 4),
        ]
        return {
            "camera": camera,
            "resolution": resolution,
            "mode": "region",
            "row_range": [r0, r1],
            "col_range": [c0, c1],
            "z_band": [z_min, z_max],
            "center_xyz": center,
            "median_xyz": [
                round(float(np.median(xs)), 4),
                round(float(np.median(ys)), 4),
                round(float(np.median(zs)), 4),
            ],
            "n_valid": int(pts.shape[0]),
            "step": nn,
            "image_size": [height, width],
            "source_artifact": source_artifact,
        }

    if row < 0 or row >= height or col < 0 or col >= width:
        return {
            "error": (
                f"pixel ({row},{col}) out of bounds; {camera} image is "
                f"{height}x{width}"
            )
        }

    depth_m = None
    if source_artifact == low_artifact:
        try:
            depth = _load_depth(camera, nn)
        except Exception as e:
            return {"error": f"{camera} depth not found for step {nn}: {e}"}
        depth_m = float(depth[row, col])
        if not np.isfinite(depth_m) or depth_m <= 0 or depth_m > 10:
            return {
                "error": (
                    f"invalid {camera} depth {depth_m:.3f}m at pixel "
                    f"({row},{col}); pick a different pixel"
                )
            }
    world_xyz_raw = world_map[row, col]
    if (
        not np.isfinite(world_xyz_raw).all()
        or float(np.abs(world_xyz_raw[:3]).sum()) <= 1e-6
    ):
        return {"error": f"invalid {camera} world xyz at pixel ({row},{col})"}
    world_xyz = [round(float(v), 4) for v in world_xyz_raw[:3]]

    out = {
        "camera": camera,
        "resolution": resolution,
        "pixel": [row, col],
        "world_xyz": world_xyz,
        "step": nn,
        "image_size": [height, width],
        "source_artifact": source_artifact,
    }
    if depth_m is not None:
        out["depth_m"] = round(depth_m, 4)
    return out
