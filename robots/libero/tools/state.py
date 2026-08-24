"""The ``states.json`` trace: dumping it, reading it back, exporting recipes.

This module owns the run's state trace in both directions — :func:`dump_state`
writes one step (state blob + every per-step image/depth/world artifact), and
the ``_load_*`` readers plus the :func:`view_driver_state` tool read it back.
Deliberately no privileged object coordinates are recorded; the agent must
localize through the visual artifacts.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

import imageio.v2 as imageio
import numpy as np

from rpent.utils.logging import get_logger, get_output_dir

from robots.libero.tools.artifacts import (
    ARTIFACT_DIRECTORIES,
    _artifact_relative_path,
    artifact_path,
)
from robots.libero.tools.catalog import PRIMITIVE_TOOL_NAMES
from robots.libero.tools.geometry import _metric_depth, _world_from_depth

if TYPE_CHECKING:
    from robots.libero.tools.primitives import LiberoPrimitives

logger = get_logger("libero")


# ---------------------------------------------------------------------------
# State artifacts
# ---------------------------------------------------------------------------


def _append_state(output_dir: str, blob: dict) -> None:
    """Append *blob* to ``<output_dir>/states.json`` atomically."""
    path = artifact_path(output_dir, "states")
    tmp_path = path.parent / f"{path.name}.tmp"
    if path.exists():
        with open(path) as f:
            states = json.load(f)
    else:
        states = []
    states.append(blob)
    with open(tmp_path, "w") as f:
        json.dump(states, f, indent=2)
    os.replace(tmp_path, path)


def write_recipe_from_states(output_dir: str, recipe_tag: str) -> str:
    """Find a command sequence that gets ``libero_terminated=True``.

    Export non-error LIBERO primitive commands from ``states.json`` and
    successful segment calls from ``segments/segment_*.json``.
    """
    states_path = artifact_path(output_dir, "states")
    if states_path.exists():
        with open(states_path) as f:
            states = json.load(f)
    else:
        states = []

    command_events = []
    for step_idx, entry in enumerate(states):
        if not entry:
            continue
        command = entry.get("command")
        if command is None:
            continue
        if command.get("action") not in PRIMITIVE_TOOL_NAMES:
            continue
        result = entry.get("result")
        if isinstance(result, dict) and result.get("error"):
            continue
        command_events.append(((step_idx, -1), command))

    for artifact in artifact_path(output_dir, "segments").glob("segment_*.json"):
        with artifact.open() as f:
            segment = json.load(f)
        if segment.get("error"):
            continue
        if segment["mode"] == "text":
            command = {
                "action": "segment",
                "prompt": segment["prompt"],
                "camera": segment["camera"],
            }
        else:
            command = {
                "action": "segment",
                "point": segment["point"],
                "camera": segment["camera"],
            }
        source_step = int(segment["source_step"])
        event_order = (source_step, int(segment["segment_index"]))
        command_events.append((event_order, command))

    recipe_path = os.path.join(output_dir, f"recipe_{recipe_tag}.jsonl")
    tmp_path = recipe_path + ".tmp"
    command_events.sort(key=lambda event: event[0])
    with open(tmp_path, "w") as f:
        for _, command in command_events:
            f.write(json.dumps(command, separators=(",", ":")) + "\n")
    os.replace(tmp_path, recipe_path)
    return recipe_path


def dump_state(primitives: LiberoPrimitives, output_dir: str, step_idx: int,
               log: dict | None = None) -> dict:
    """Dump state snapshot, images, and depth for step *step_idx*.

    Writes:
      - ``<output_dir>/images/image_NN.png``       (Pi0-frame agentview)
      - ``<output_dir>/images_cam/image_cam_NN.png`` (calibration-frame agentview)
      - ``<output_dir>/depths/depth_NN.npy``        (metric depth, meters)
      - ``<output_dir>/world/world_NN.npy``         (agentview world xyz map)
      - ``<output_dir>/images_wrist/image_wrist_NN.png``
      - ``<output_dir>/depths_wrist/depth_wrist_NN.npy``
      - ``<output_dir>/world_wrist/world_wrist_NN.npy``
      - ``<output_dir>/wrist_meta/wrist_meta_NN.json``
      - high-res ``images_cam_hi`` / ``world_hi`` artifacts
      - high-res ``images_wrist_hi`` / ``world_wrist_hi`` artifacts
      - ``<output_dir>/camera_meta.json``           (static, once)
      - appends the step blob to ``<output_dir>/states.json``

    If *log* is provided (the return value of :func:`execute`), its
    ``command``, ``result``, and ``elapsed_s`` fields are merged into the
    step blob so a single entry captures everything.
    """
    for directory in ARTIFACT_DIRECTORIES:
        (Path(output_dir) / directory).mkdir(parents=True, exist_ok=True)

    agent_world_map = None
    wrist_world_map = None
    agent_world_map_hi = None
    wrist_world_map_hi = None
    # Reuse one raw observation snapshot for state and per-step artifacts.
    raw = primitives.env.raw_obs()
    # Expose robot proprioception and object names, but never privileged
    # object coordinates; the agent must localize through visual artifacts.
    state = {
        "robot0_eef_pos": [float(x) for x in raw["robot0_eef_pos"]],
        "robot0_eef_quat": [float(x) for x in raw["robot0_eef_quat"]],
        "robot0_gripper_qpos": [float(x) for x in raw["robot0_gripper_qpos"]],
        "object_names": sorted(
            k[:-4]
            for k in raw
            if k.endswith("_pos") and "robot0" not in k and "to_robot" not in k
        ),
    }
    imageio.imwrite(
        artifact_path(output_dir, "policy_image", step=step_idx, camera="agentview", resolution="low"),
        primitives._last_obs["main_images"],
    )

    # --- camera calibration (static for agentview): fetch metadata as needed ---
    agentview_meta = primitives.env.get_camera_meta(
        camera_name="agentview",
        height=256,
        width=256,
    ) or {}
    camera_meta_path = artifact_path(output_dir, "metadata", camera="agentview", resolution="low")
    if agentview_meta and not camera_meta_path.exists():
        cam_meta_out = dict(agentview_meta)
        cam_meta_out["projection"] = (
            "Prefer the back_project(row, col, step=NN) MCP tool; it "
            "uses the 1024x1024 high-resolution world map by default. "
            "Pass resolution='low' only when row/col came from the "
            "256x256 calibration-frame image."
        )
        cam_meta_out["note"] = (
            "depth_NN.npy is in this camera frame (vertical-flipped raw "
            "buffer). image_NN.png is rotated 180deg (Pi0 convention) and "
            "is NOT in the same frame as depth/K."
        )
        with open(camera_meta_path, "w") as f:
            json.dump(cam_meta_out, f, indent=2)

    # --- per-step RGB in the depth/K frame (vertical-flip of the raw buffer) ---
    # The agent picks object pixels HERE (same frame as depth_NN.npy + K), so
    # pixel -> depth -> back-project is direct. (image_NN.png is the 180°-rotated
    # Pi0-convention frame and must NOT be used for back-projection.)
    try:
        ci = raw.get("agentview_image")
        if ci is not None:
            ci = np.asarray(ci)
            if ci.dtype != np.uint8:
                ci = ci.astype(np.uint8)
            imageio.imwrite(artifact_path(output_dir, "image", step=step_idx, camera="agentview", resolution="low"), ci[::-1])
    except Exception as e:
        logger.warning("image_cam dump failed: %s", e)

    # --- per-step metric depth (agentview), native orientation, in meters ---
    try:
        d = raw.get("agentview_depth")
        if d is not None:
            # Vertical flip to align with the camera matrices: robosuite's
            # camera_utils projection M = K_exp @ inv(extrinsic) expects the
            # depth map in this frame. VERIFIED 5/5: projecting each GT object
            # world pos via M lands on a pixel whose depth_flip[row,col] matches
            # the object's surface depth (plate Δ6mm, cookies Δ14mm). So
            # pixel(row,col) in depth_NN.npy back-projects correctly with
            # camera_meta.json (NOT the same frame as the 180°-rotated
            # image_NN.png — see camera_meta note).
            d = _metric_depth(d, agentview_meta)[::-1]
            np.save(
                artifact_path(output_dir, "depth", step=step_idx, camera="agentview", resolution="low"),
                d.astype(np.float32),
            )
            world = _world_from_depth(d, agentview_meta).astype(np.float32)
            np.save(
                artifact_path(output_dir, "world", step=step_idx, camera="agentview", resolution="low"),
                world,
            )
            agent_world_map = _artifact_relative_path(
                step_idx, "agentview", "low", "world"
            )
    except Exception as e:
        logger.warning("depth dump failed: %s", e)

    # --- per-step wrist camera (robot0_eye_in_hand), calibration frame ---
    try:
        wimg = raw.get("robot0_eye_in_hand_image")
        if wimg is None:
            logger.warning("wrist image missing from raw_obs")
        else:
            wimg = np.asarray(wimg)
            if wimg.dtype != np.uint8:
                wimg = wimg.astype(np.uint8)
            imageio.imwrite(artifact_path(output_dir, "image", step=step_idx, camera="wrist", resolution="low"), wimg[::-1])
    except Exception as e:
        logger.warning("wrist image dump failed: %s", e)

    try:
        wdpt = raw.get("robot0_eye_in_hand_depth")
        if wdpt is None:
            logger.warning("wrist depth missing from raw_obs")
        else:
            wdpt_arr = np.asarray(wdpt, dtype=np.float32)
            height, width = wdpt_arr.shape[:2]
            wmeta = primitives.env.get_camera_meta(
                camera_name="robot0_eye_in_hand",
                height=int(height),
                width=int(width),
            )
            if wmeta is None:
                logger.warning("wrist camera meta missing; skipping wrist depth/world")
            else:
                wdpt_metric = _metric_depth(wdpt_arr, wmeta)[::-1]
                np.save(
                    artifact_path(output_dir, "depth", step=step_idx, camera="wrist", resolution="low"),
                    wdpt_metric.astype(np.float32),
                )
                world_w = _world_from_depth(wdpt_metric, wmeta).astype(np.float32)
                np.save(
                    artifact_path(output_dir, "world", step=step_idx, camera="wrist", resolution="low"),
                    world_w,
                )
                wrist_world_map = _artifact_relative_path(
                    step_idx, "wrist", "low", "world"
                )

                wmeta_out = dict(wmeta)
                wmeta_out["note"] = (
                    "MOVING camera: extrinsic_cam2world is for THIS step "
                    "only. world_wrist_NN.npy[row,col] gives world "
                    "(x,y,z) for that pixel, in the SAME world frame as "
                    "agentview world_NN.npy."
                )
                with open(
                    artifact_path(output_dir, "metadata", step=step_idx, camera="wrist", resolution="low"),
                    "w",
                ) as f:
                    json.dump(wmeta_out, f, indent=2)
    except Exception as e:
        logger.warning("wrist depth/world dump failed: %s", e)

    try:
        rgb_hi, depth_hi = primitives.env.render_camera(
            camera_name="agentview",
            height=1024,
            width=1024,
            depth=True,
        )
        meta_hi = primitives.env.get_camera_meta("agentview", 1024, 1024)
        if meta_hi is None:
            raise RuntimeError("agentview camera metadata missing")
        imageio.imwrite(
            artifact_path(output_dir, "image", step=step_idx, camera="agentview", resolution="high"),
            np.asarray(rgb_hi)[::-1],
        )
        world_hi = _world_from_depth(
            _metric_depth(depth_hi, meta_hi)[::-1],
            meta_hi,
        ).astype(np.float16)
        np.save(
            artifact_path(output_dir, "world", step=step_idx, camera="agentview", resolution="high"),
            world_hi,
        )
        agent_world_map_hi = _artifact_relative_path(
            step_idx, "agentview", "high", "world"
        )
    except Exception as e:
        logger.warning("agentview high-res dump failed: %s", e)

    try:
        rgb_wrist_hi, depth_wrist_hi = primitives.env.render_camera(
            camera_name="robot0_eye_in_hand",
            height=1024,
            width=1024,
            depth=True,
        )
        meta_wrist_hi = primitives.env.get_camera_meta(
            "robot0_eye_in_hand", 1024, 1024
        )
        if meta_wrist_hi is None:
            raise RuntimeError("robot0_eye_in_hand camera metadata missing")
        imageio.imwrite(
            artifact_path(output_dir, "image", step=step_idx, camera="wrist", resolution="high"),
            np.asarray(rgb_wrist_hi)[::-1],
        )
        world_wrist_hi = _world_from_depth(
            _metric_depth(depth_wrist_hi, meta_wrist_hi)[::-1],
            meta_wrist_hi,
        ).astype(np.float16)
        np.save(
            artifact_path(output_dir, "world", step=step_idx, camera="wrist", resolution="high"),
            world_wrist_hi,
        )
        wrist_world_map_hi = _artifact_relative_path(
            step_idx, "wrist", "high", "world"
        )
    except Exception as e:
        logger.warning("wrist high-res dump failed: %s", e)

    for old_step in range(max(0, int(step_idx) - 4)):
        for path in (
            artifact_path(output_dir, "image", step=old_step, camera="agentview", resolution="high"),
            artifact_path(output_dir, "world", step=old_step, camera="agentview", resolution="high"),
            artifact_path(output_dir, "image", step=old_step, camera="wrist", resolution="high"),
            artifact_path(output_dir, "world", step=old_step, camera="wrist", resolution="high"),
        ):
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass

    blob = {
        "step_idx": step_idx,
        "libero_terminated": primitives.env.episode_terminated,
        "episode_truncated": primitives.env.episode_truncated,
        "task_language": primitives.env.get_task_language(),
        "state": state,
        "world_map": agent_world_map,
        "wrist_world_map": wrist_world_map,
        "world_map_hi": agent_world_map_hi,
        "wrist_world_map_hi": wrist_world_map_hi,
    }
    # Merge the execution log (command + result + elapsed_s) into the
    # state blob so a single entry captures everything for the step.
    if log is not None:
        blob["command"] = log.get("command")
        blob["result"] = log.get("result")
        blob["elapsed_s"] = log.get("elapsed_s")
    _append_state(output_dir, blob)
    return blob


# ---------------------------------------------------------------------------
# State trace readers
# ---------------------------------------------------------------------------


def _load_states() -> list:
    """Return the parsed state trace from the local output dir."""
    path = artifact_path(get_output_dir(), "states")
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def _latest_step() -> int | None:
    states = _load_states()
    if not states:
        return None
    return states[-1]["step_idx"]


def _load_step(nn: int) -> dict:
    """Look up the state blob for step ``nn`` from states.json."""
    for entry in _load_states():
        if entry.get("step_idx") == nn:
            return entry
    raise FileNotFoundError(f"step {nn} not present in states.json")


def _load_image_path(nn: int, kind: str) -> str | None:
    """Return the path to a dumped state image. None if not present."""
    out_dir = get_output_dir()
    if kind == "agent":
        path = artifact_path(out_dir, "policy_image", step=nn, camera="agentview", resolution="low")
    elif kind == "camera":
        path = artifact_path(out_dir, "image", step=nn, camera="agentview", resolution="low")
    elif kind == "wrist":
        path = artifact_path(out_dir, "image", step=nn, camera="wrist", resolution="low")
    else:
        raise ValueError(f"unknown image kind: {kind}")
    if not path.exists():
        return None
    return str(path)


def _load_camera_meta(camera: str = "agentview", nn: int | None = None) -> dict:
    out_dir = get_output_dir()
    if camera == "agentview":
        path = artifact_path(out_dir, "metadata", camera="agentview", resolution="low")
    elif camera == "wrist" and nn is not None:
        path = artifact_path(out_dir, "metadata", step=nn, camera="wrist", resolution="low")
    else:
        raise ValueError("camera must be 'agentview' or 'wrist' with nn")
    if not path.exists():
        raise FileNotFoundError(f"{path.name} not found in {out_dir}")
    with open(path) as f:
        return json.load(f)


def _load_depth(camera: str, nn: int) -> np.ndarray:
    out_dir = get_output_dir()
    if camera not in ("agentview", "wrist"):
        raise ValueError("camera must be 'agentview' or 'wrist'")
    path = artifact_path(out_dir, "depth", step=nn, camera=camera, resolution="low")
    if not path.exists():
        raise FileNotFoundError(f"{path.name} not found in {out_dir}")
    depth = np.load(path)
    if depth.ndim == 3:
        depth = depth[..., 0]
    return depth


def view_driver_state(step: int | None = None) -> dict:
    latest = _latest_step()
    if latest is None:
        return {"error": "no state entries; env not ready"}
    nn = latest if step is None else int(step)
    try:
        data = _load_step(nn)
    except Exception as e:
        return {"error": f"step {nn} not present in state trace: {e}"}

    out: dict = {"step": nn}
    out["task_language"] = data.get("task_language")
    # Default to {} (not the entire blob) when "state" is missing — otherwise
    # command/result/vla_desync would bleed into the "state" field, confusing
    # the LLM about what robot state actually contains.
    out["state"] = data.get("state", {})
    out["libero_terminated"] = data.get("libero_terminated")
    out["episode_truncated"] = data.get("episode_truncated")
    out["world_map"] = data.get("world_map")
    out["wrist_world_map"] = data.get("wrist_world_map")
    out["world_map_hi"] = data.get("world_map_hi")
    out["wrist_world_map_hi"] = data.get("wrist_world_map_hi")
    out["log"] = {
        "command": data.get("command"),
        "result": data.get("result"),
        "elapsed_s": data.get("elapsed_s"),
    }
    for field, kind in (
        ("image_path", "agent"),
        ("image_cam_path", "camera"),
        ("image_wrist_path", "wrist"),
    ):
        image_path = _load_image_path(nn, kind)
        if image_path:
            out[field] = image_path
    for field, camera in (
        ("image_cam_hi_path", "agentview"),
        ("image_wrist_hi_path", "wrist"),
    ):
        image_path = artifact_path(get_output_dir(), "image", step=nn, camera=camera, resolution="high")
        if image_path.exists():
            out[field] = str(image_path)
    return out
