"""World xyz -> pixel, via the stored world maps.

No camera math and no re-rendering: every step already ships a per-pixel
world-XYZ map, so "where is this 3D point in the image" is a nearest-
neighbour lookup in an artifact that is itself evidence. The returned
``err_m`` is the distance between the query and the best pixel's world
point — a large error means the point was not visible from that camera at
that step (occluded or out of frame), and the caller should say so rather
than draw a confident dot.
"""
from __future__ import annotations

import struct
from pathlib import Path

import numpy as np

#: (camera, resolution) -> (subdir, filename pattern)
WORLD_MAPS: dict[tuple[str, str], tuple[str, str]] = {
    ("agentview", "low"): ("world", "world_{step:02d}.npy"),
    ("agentview", "high"): ("world_hi", "world_hi_{step:02d}.npy"),
    ("wrist", "low"): ("world_wrist", "world_wrist_{step:02d}.npy"),
    ("wrist", "high"): ("world_wrist_hi", "world_wrist_hi_{step:02d}.npy"),
}

#: (camera, resolution) -> (subdir, filename pattern) of the matching RGB frame
IMAGES: dict[tuple[str, str], tuple[str, str]] = {
    ("agentview", "low"): ("images_cam", "image_cam_{step:02d}.png"),
    ("agentview", "high"): ("images_cam_hi", "image_cam_hi_{step:02d}.png"),
    ("wrist", "low"): ("images_wrist", "image_wrist_{step:02d}.png"),
    ("wrist", "high"): ("images_wrist_hi", "image_wrist_hi_{step:02d}.png"),
}


def image_relpath(
    run_dir: Path, step: int, camera: str = "agentview", resolution: str = "low"
) -> str | None:
    """Relative path of the RGB frame, or None if it was not dumped."""
    sub, pattern = IMAGES[(camera, resolution)]
    rel = f"{sub}/{pattern.format(step=step)}"
    return rel if (Path(run_dir) / rel).exists() else None


def world_to_pixel(
    run_dir: Path,
    step: int,
    xyz,
    camera: str = "agentview",
    resolution: str = "low",
) -> tuple[int, int, float] | None:
    """(row, col, err_m) of the pixel whose world point is nearest ``xyz``.

    None when the step has no stored map for that camera/resolution.
    """
    sub, pattern = WORLD_MAPS[(camera, resolution)]
    path = Path(run_dir) / sub / pattern.format(step=step)
    if not path.exists():
        return None
    world = np.load(path).astype(np.float32)
    target = np.asarray(xyz, dtype=np.float32)
    if world.ndim != 3 or world.shape[-1] != 3 or target.shape != (3,):
        return None
    dist = np.linalg.norm(world - target, axis=-1)
    invalid = ~np.isfinite(world).all(axis=-1) | (np.abs(world).sum(axis=-1) == 0)
    dist[invalid] = np.inf
    flat = int(np.argmin(dist))
    row, col = divmod(flat, dist.shape[1])
    err = float(dist[row, col])
    if not np.isfinite(err):
        return None
    return row, col, err


def png_size(path: Path) -> tuple[int, int] | None:
    """(width, height) from the PNG IHDR chunk — stdlib, no image library."""
    try:
        with open(path, "rb") as f:
            header = f.read(26)
    except OSError:
        return None
    if len(header) < 26 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", header[16:24])
    return int(width), int(height)
