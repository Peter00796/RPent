"""Canonical run-artifact layout for the LIBERO toolkit.

``ARTIFACT_LAYOUT`` is the single source of truth for every path the toolkit
writes, and :func:`artifact_path` is the only supported way to resolve one.
The path schema is an interface: it is consumed by the agent, by the dashboard,
and by offline diagnostics, so editing a template changes an interface.
"""
from __future__ import annotations

import os
from pathlib import Path

ARTIFACT_LAYOUT: dict[tuple[str | None, str | None, str], str] = {
    ("agentview", "low", "policy_image"): "images/image_{step:02d}.png",
    ("agentview", "low", "image"): "images_cam/image_cam_{step:02d}.png",
    ("agentview", "low", "depth"): "depths/depth_{step:02d}.npy",
    ("agentview", "low", "world"): "world/world_{step:02d}.npy",
    ("agentview", "low", "metadata"): "camera_meta.json",
    ("agentview", "high", "image"): "images_cam_hi/image_cam_hi_{step:02d}.png",
    ("agentview", "high", "world"): "world_hi/world_hi_{step:02d}.npy",
    ("wrist", "low", "image"): "images_wrist/image_wrist_{step:02d}.png",
    ("wrist", "low", "depth"): "depths_wrist/depth_wrist_{step:02d}.npy",
    ("wrist", "low", "world"): "world_wrist/world_wrist_{step:02d}.npy",
    ("wrist", "low", "metadata"): "wrist_meta/wrist_meta_{step:02d}.json",
    ("wrist", "high", "image"): "images_wrist_hi/image_wrist_hi_{step:02d}.png",
    ("wrist", "high", "world"): "world_wrist_hi/world_wrist_hi_{step:02d}.npy",
    (None, None, "states"): "states.json",
    (None, None, "episode_video"): "episode.mp4",
    (None, None, "segments"): "segments",
    (None, None, "action_videos"): "action_videos",
    # Derived, not raw: an index over the segment artifacts, written by the
    # tool layer and safe to regenerate. Lives under analysis/ to keep it
    # distinct from the immutable per-step evidence above.
    (None, None, "entities"): "analysis/entities.json",
}
ARTIFACT_DIRECTORIES: tuple[str, ...] = (
    "images",
    "images_cam",
    "depths",
    "world",
    "images_cam_hi",
    "world_hi",
    "images_wrist",
    "depths_wrist",
    "world_wrist",
    "wrist_meta",
    "images_wrist_hi",
    "world_wrist_hi",
    "segments",
    "action_videos",
    "analysis",
)


def protected_paths(output_dir: str | os.PathLike[str]) -> tuple[Path, ...]:
    """Every top-level path the toolkit owns inside the output dir.

    These are the run's evidence — the sandbox registers them as read-only to
    the agent (``sandbox.add_write_protection``), so a run's record cannot be
    rewritten by the agent it records. Derived from ``ARTIFACT_LAYOUT`` so a
    new artifact kind is protected by construction, not by remembering.
    """
    out = Path(output_dir)
    names = {template.split("/")[0] for template in ARTIFACT_LAYOUT.values()}
    return tuple(sorted(out / name for name in names))


def artifact_path(
    output_dir: str | os.PathLike[str],
    kind: str,
    *,
    step: int | None = None,
    camera: str | None = None,
    resolution: str | None = None,
) -> Path:
    """Resolve one artifact path from the shared layout.

    ``kind`` identifies the artifact; the remaining fields are optional
    qualifiers and must be passed by keyword to avoid mixing them up.
    """
    return Path(output_dir) / _artifact_relative_path(step, camera, resolution, kind)


def _artifact_relative_path(
    step: int | None,
    camera: str | None,
    resolution: str | None,
    kind: str,
) -> str:
    template = ARTIFACT_LAYOUT[(camera, resolution, kind)]
    if step is None and "{step" in template:
        raise ValueError(f"{kind} artifact requires a step")
    return template.format(step=step)
