"""One renderer per tool: each tool knows how to draw its own evidence.

``REGISTRY`` maps a tool name to a function ``(call, run) -> Card``. Adding a
tool to the harness means adding one renderer here (or accepting the generic
args/result card). Renderers only READ artifacts — a replay must never
compute new evidence, only display what the run recorded; the one allowed
derivation is projecting a recorded 3D point onto a recorded world map
(:mod:`.project`), which is how a coordinate becomes a visible dot.

Marker kinds the HTML layer understands: ``point`` (circle), ``target``
(X), ``box`` (rectangle, pixel coords). A projection with err_m above
``VISIBILITY_ERR_M`` is drawn as a warning line instead of a dot — an
occluded point must not look like a confident one.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from rpent.replay import project
from rpent.replay.loader import Call, RunReplay

#: Above this projection error the point was not visible from the camera.
VISIBILITY_ERR_M = 0.05


@dataclass
class Marker:
    row: float
    col: float
    label: str
    kind: str = "point"  # point | target
    row2: float | None = None  # boxes: opposite corner
    col2: float | None = None


@dataclass
class Panel:
    """One image with SVG markers over it."""

    src: str                       # path relative to the run dir
    width: int
    height: int
    markers: list[Marker] = field(default_factory=list)
    caption: str = ""


@dataclass
class Card:
    title: str
    lines: list[str] = field(default_factory=list)
    panels: list[Panel] = field(default_factory=list)
    raw: str = ""                  # full result JSON for the <details> fold


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _short(value, limit: int = 240) -> str:
    text = json.dumps(value, default=str) if not isinstance(value, str) else value
    return text if len(text) <= limit else text[:limit] + "…"


def _raw(result) -> str:
    try:
        return json.dumps(result, indent=2, default=str)
    except Exception:
        return str(result)


def _panel(run: RunReplay, step: int | None, camera: str = "agentview",
           resolution: str = "low", caption: str = "") -> Panel | None:
    if step is None:
        return None
    rel = project.image_relpath(run.run_dir, step, camera, resolution)
    if rel is None:
        return None
    size = project.png_size(run.run_dir / rel)
    if size is None:
        return None
    return Panel(src=rel, width=size[0], height=size[1],
                 caption=caption or f"{camera} @ step {step}")


def _mark_world_point(panel: Panel, run: RunReplay, step: int, xyz, label: str,
                      kind: str, camera: str, resolution: str,
                      lines: list[str]) -> None:
    """Project a recorded 3D point onto the panel, or say why not."""
    hit = project.world_to_pixel(run.run_dir, step, xyz, camera, resolution)
    if hit is None:
        lines.append(f"{label}: no world map stored for step {step} — not drawn")
        return
    row, col, err = hit
    if err > VISIBILITY_ERR_M:
        lines.append(
            f"{label}: not visible from {camera} at step {step} "
            f"(nearest map point is {err:.3f} m away) — not drawn"
        )
        return
    panel.markers.append(Marker(row=row, col=col, label=label, kind=kind))


def _eef(run: RunReplay, step: int | None):
    return (run.state_at(step).get("state") or {}).get("robot0_eef_pos")


def _relativize(recorded_path: object, run_dir: Path) -> str | None:
    """Map an absolute path recorded on the run machine into this run dir.

    Records carry absolute paths from wherever the run executed; the replay
    may be built on another machine from a copied directory. Match on the
    run-dir name when present, else fall back to the last two components
    (the ``<artifact_dir>/<file>`` shape every layout entry has).
    """
    if not recorded_path:
        return None
    parts = Path(str(recorded_path)).parts
    if run_dir.name in parts:
        rel = Path(*parts[parts.index(run_dir.name) + 1:])
    else:
        rel = Path(*parts[-2:])
    return str(rel) if (run_dir / rel).exists() else None


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------

def _generic(call: Call, run: RunReplay) -> Card:
    card = Card(title=call.tool, raw=_raw(call.result))
    card.lines.append(f"args: {_short(call.args)}")
    if isinstance(call.result, dict) and call.result.get("error"):
        card.lines.append(f"ERROR: {_short(call.result['error'])}")
    else:
        card.lines.append(f"result: {_short(call.result)}")
    return card


def _view_driver_state(call: Call, run: RunReplay) -> Card:
    card = Card(title="view_driver_state", raw=_raw(call.result))
    result = call.result if isinstance(call.result, dict) else {}
    step = result.get("step", call.args.get("step"))
    state = result.get("state") or {}
    if state.get("robot0_eef_pos"):
        eef = state["robot0_eef_pos"]
        card.lines.append(f"eef @ ({eef[0]:.3f}, {eef[1]:.3f}, {eef[2]:.3f})")
    if result.get("libero_terminated") is not None:
        card.lines.append(f"libero_terminated: {result['libero_terminated']}")
    panel = _panel(run, step)
    if panel:
        if state.get("robot0_eef_pos"):
            _mark_world_point(panel, run, step, state["robot0_eef_pos"], "eef",
                              "point", "agentview", "low", card.lines)
        card.panels.append(panel)
    return card


def _segment(call: Call, run: RunReplay) -> Card:
    result = call.result if isinstance(call.result, dict) else {}
    entity = call.args.get("entity") or ""
    title = f"segment({call.args.get('prompt') or call.args.get('point')!r})"
    if entity:
        title += f" → entity '{entity}'"
    card = Card(title=title, raw=_raw(call.result))
    if not result or result.get("error") or result.get("found") is False:
        card.lines.append(f"NOT FOUND / error: {_short(result.get('error') or result)}")
        return card

    step = result.get("step", result.get("source_step"))
    camera = result.get("camera", call.args.get("camera", "agentview"))
    card.lines.append(
        f"camera {camera}, step {step}, score {result.get('score')}, "
        f"{result.get('n_pixels')} mask px"
    )
    if result.get("world_xyz"):
        xyz = result["world_xyz"]
        card.lines.append(f"world_xyz ({xyz[0]:.3f}, {xyz[1]:.3f}, {xyz[2]:.3f})")
    shape = result.get("shape") or {}
    if shape:
        foot = shape.get("footprint") or {}
        card.lines.append(
            f"shape: {shape.get('orientation')}, graspable_width "
            f"{foot.get('short_extent_m')}, short-axis yaw {foot.get('short_axis_yaw_deg')}°"
            + (" (yaw not meaningful)" if not shape.get("yaw_is_meaningful") else "")
        )
    rim = result.get("rim") or {}
    if rim:
        card.lines.append(
            f"rim center {rim.get('xy_bbox_center')}, retreat {rim.get('retreat_direction')}"
        )
    if result.get("looks_hollow") is not None:
        card.lines.append(f"looks_hollow: {result['looks_hollow']}")
    if result.get("registered"):
        card.lines.append(f"registered: {_short(result['registered'])}")

    # The stored overlay IS the evidence for "which pixels the mask claimed".
    # SAM's box is [x0, y0, x1, y1] in the overlay's pixel space (verified
    # against a world-map projection of the same object).
    rel = _relativize(result.get("overlay_path"), run.run_dir)
    if rel:
        size = project.png_size(run.run_dir / rel)
        if size:
            panel = Panel(src=rel, width=size[0], height=size[1],
                          caption=f"mask overlay ({camera} @ step {step})")
            box = result.get("box")
            if isinstance(box, (list, tuple)) and len(box) == 4:
                x0, y0, x1, y1 = (float(v) for v in box)
                panel.markers.append(Marker(row=y0, col=x0, row2=y1, col2=x1,
                                            label="mask bbox", kind="box"))
            card.panels.append(panel)
    return card


def _back_project(call: Call, run: RunReplay) -> Card:
    card = Card(title="back_project", raw=_raw(call.result))
    result = call.result if isinstance(call.result, dict) else {}
    camera = call.args.get("camera", "agentview")
    resolution = call.args.get("resolution", "high")
    step = call.args.get("step")
    if step is None and isinstance(result, dict):
        step = result.get("step")
    if result.get("world_xyz"):
        xyz = result["world_xyz"]
        card.lines.append(f"world_xyz ({xyz[0]:.3f}, {xyz[1]:.3f}, {xyz[2]:.3f})")
    if result.get("error"):
        card.lines.append(f"ERROR: {_short(result['error'])}")
    panel = _panel(run, step, camera, resolution) if step is not None else None
    if panel:
        if call.args.get("row") is not None and call.args.get("col") is not None:
            panel.markers.append(Marker(row=float(call.args["row"]),
                                        col=float(call.args["col"]),
                                        label="queried pixel", kind="target"))
        if call.args.get("row_range") and call.args.get("col_range"):
            r0, r1 = call.args["row_range"]
            c0, c1 = call.args["col_range"]
            panel.markers.append(Marker(row=float(r0), col=float(c0),
                                        row2=float(r1), col2=float(c1),
                                        label="queried region", kind="box"))
        card.panels.append(panel)
    return card


def _motion(call: Call, run: RunReplay) -> Card:
    card = Card(title=call.tool, raw=_raw(call.result))
    result = call.result if isinstance(call.result, dict) else {}
    target = call.args.get("xyz")
    if target:
        card.lines.append(
            f"target ({target[0]:.3f}, {target[1]:.3f}, {target[2]:.3f}), "
            f"gripper {call.args.get('gripper')}"
        )
    inner = result.get("result") if isinstance(result.get("result"), dict) else result
    dist = inner.get("final_dist_m") if isinstance(inner, dict) else None
    if isinstance(dist, (int, float)):
        stalled = dist > 0.02
        card.lines.append(f"final_dist_m {dist:.4f}" + ("  ⚠ STALLED" if stalled else ""))
    before = _panel(run, call.step_before, caption=f"before (step {call.step_before})")
    if before:
        if target:
            _mark_world_point(before, run, call.step_before, target, "target",
                              "target", "agentview", "low", card.lines)
        eef = _eef(run, call.step_before)
        if eef:
            _mark_world_point(before, run, call.step_before, eef, "eef",
                              "point", "agentview", "low", card.lines)
        card.panels.append(before)
    after = _panel(run, call.step_after, caption=f"after (step {call.step_after})")
    if after and call.advanced:
        eef = _eef(run, call.step_after)
        if eef:
            _mark_world_point(after, run, call.step_after, eef, "eef now",
                              "point", "agentview", "low", card.lines)
        if target:
            _mark_world_point(after, run, call.step_after, target, "target",
                              "target", "agentview", "low", card.lines)
        card.panels.append(after)
    return card


def _vla(call: Call, run: RunReplay) -> Card:
    card = Card(title=f"{call.tool}({call.args.get('prompt')!r})", raw=_raw(call.result))
    result = call.result if isinstance(call.result, dict) else {}
    inner = result.get("result") if isinstance(result.get("result"), dict) else result
    if isinstance(inner, dict):
        for key in ("success", "task_success", "chunks_used", "lifted", "gripper_closed"):
            if key in inner:
                card.lines.append(f"{key}: {inner[key]}")
    before = _panel(run, call.step_before, caption=f"before (step {call.step_before})")
    after = _panel(run, call.step_after, caption=f"after (step {call.step_after})")
    card.panels.extend(p for p in (before, after) if p)
    return card


def _world_extent(call: Call, run: RunReplay) -> Card:
    card = Card(title=f"world_extent(mode={call.args.get('mode', 'occupancy')!r})",
                raw=_raw(call.result))
    result = call.result if isinstance(call.result, dict) else {}
    for key in ("mode", "n_points_in_box", "occupied_voxels", "nearest_surface",
                "held_object", "offset_from_eef", "extent"):
        if key in result:
            card.lines.append(f"{key}: {_short(result[key])}")
    if result.get("error"):
        card.lines.append(f"ERROR: {_short(result['error'])}")
    step = call.args.get("step")
    panel = _panel(run, step) if step is not None else None
    if panel:
        card.panels.append(panel)
    return card


def _compare_extent(call: Call, run: RunReplay) -> Card:
    card = Card(title="compare_extent", raw=_raw(call.result))
    result = call.result if isinstance(call.result, dict) else {}
    for key in ("voxels_added", "voxels_removed", "n_points_in_box_a",
                "n_points_in_box_b", "step_a", "step_b"):
        if key in result:
            card.lines.append(f"{key}: {_short(result[key])}")
    step_a = result.get("step_a", call.args.get("step_a"))
    step_b = result.get("step_b", call.args.get("step_b"))
    for step, tag in ((step_a, "step_a"), (step_b, "step_b")):
        panel = _panel(run, step, caption=f"{tag} = {step}") if step is not None else None
        if panel:
            card.panels.append(panel)
    return card


#: tool name -> renderer. THE extension point: one entry per tool.
REGISTRY = {
    "view_driver_state": _view_driver_state,
    "segment": _segment,
    "back_project": _back_project,
    "move_to": _motion,
    "move_pose": _motion,
    "rotate_wrist": _motion,
    "rotate_pitch": _motion,
    "release": _motion,
    "set_gripper": _motion,
    "pi0_pick": _vla,
    "pi0_doubled": _vla,
    "world_extent": _world_extent,
    "compare_extent": _compare_extent,
    # view_camera_meta, read/write/list/finish/read_image fall through to the
    # generic args/result card — nothing visual to reconstruct.
}


def render_call(call: Call, run: RunReplay) -> Card:
    renderer = REGISTRY.get(call.tool, _generic)
    try:
        return renderer(call, run)
    except Exception as exc:  # a broken renderer must not sink the replay
        card = _generic(call, run)
        card.lines.append(f"[renderer error: {type(exc).__name__}: {exc}]")
        return card
