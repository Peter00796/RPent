"""The 3D evidence replay: point-cloud slider + a call panel in lockstep.

Port of the box-side ``scripts/replay_run_3d.py`` (same scene construction:
world maps as true-colour clouds, SAM answers accumulating, motion target,
eef path, gripper-width callouts) with the evidence timeline joined in:

- SAM markers come from the CALL LOG, so they carry seq, entity name and
  score — the same identity the proposals cite;
- a side panel follows the slider and shows, for the selected env step, the
  reasoning and tool calls issued while the world was in that state, each
  deep-linking to ``replay.html#seq-N`` for the full 2D card;
- the run header carries the sandbox profile and finish verdict.

Plotly is loaded from its CDN like the original — the clouds are megabytes
of JSON already, so this file is for interactive review, not archival; the
archival record stays the artifacts themselves plus ``replay.html``.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from rpent.replay.loader import Call, RunReplay
from rpent.replay.markdown import render_markdown
from rpent.replay.render import render_call

_PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"


# ---------------------------------------------------------------------------
# Scene construction (ported from scripts/replay_run_3d.py)
# ---------------------------------------------------------------------------

def _frame_sources(run_dir: Path, prefer_hi: bool) -> dict[int, tuple[Path, Path | None]]:
    """step -> (world npy, rgb png or None), for every step with a map."""
    order = (("world_hi", "images_cam_hi"), ("world", "images_cam"))
    if not prefer_hi:
        order = order[::-1]
    frames: dict[int, tuple[Path, Path | None]] = {}
    for sub, img_sub in order:
        for f in sorted((run_dir / sub).glob("*.npy")):
            step = int(f.stem.rsplit("_", 1)[1])
            if step in frames:
                continue
            rgbs = list((run_dir / img_sub).glob(f"*{f.stem.rsplit('_', 1)[1]}.png"))
            frames[step] = (f, rgbs[0] if rgbs else None)
    return dict(sorted(frames.items()))


def _read_rgb(path: Path) -> np.ndarray | None:
    """RGB array via imageio or PIL, whichever is installed; None otherwise."""
    try:
        import imageio.v2 as imageio  # project dependency, but optional here
        return np.asarray(imageio.imread(path))[..., :3]
    except Exception:
        pass
    try:
        from PIL import Image
        return np.asarray(Image.open(path).convert("RGB"))
    except Exception:
        return None


def _cloud(world_path: Path, rgb_path: Path | None, stride: int, bounds):
    world = np.load(world_path).astype(np.float32)[::stride, ::stride]
    pts = world.reshape(-1, 3)
    ok = np.isfinite(pts).all(1) & (np.abs(pts).sum(1) > 0)
    cols = None
    if rgb_path is not None:
        rgb = _read_rgb(rgb_path)
        if rgb is not None and rgb.shape[0] == np.load(world_path, mmap_mode="r").shape[0]:
            cols = rgb[::stride, ::stride].reshape(-1, 3)[ok]
    pts = pts[ok]
    if bounds is not None:
        lo, hi = bounds
        keep = np.all((pts >= lo) & (pts <= hi), axis=1)
        pts = pts[keep]
        cols = cols[keep] if cols is not None else None
    return pts, cols


def _segment_hits(run: RunReplay) -> list[dict]:
    """Successful segment calls, with seq/entity — the run's belief history."""
    hits = []
    for call in run.calls:
        if call.tool != "segment" or not isinstance(call.result, dict):
            continue
        result = call.result
        if result.get("error") or result.get("found") is False or not result.get("world_xyz"):
            continue
        hits.append({
            "seq": call.seq,
            "step": result.get("step", result.get("source_step")) or 0,
            "xyz": [float(v) for v in result["world_xyz"]],
            "entity": call.args.get("entity") or "",
            "prompt": str(call.args.get("prompt") or "")[:44],
            "score": result.get("score"),
        })
    return hits


def _bounds(run: RunReplay, hits: list[dict], pad: float = 0.18):
    points = [h["xyz"] for h in hits]
    for entry in run.states:
        cmd = entry.get("command") or {}
        target = cmd.get("xyz") or (entry.get("result") or {}).get("target_xyz")
        if target:
            points.append([float(v) for v in target])
        eef = (entry.get("state") or {}).get("robot0_eef_pos")
        if eef:
            points.append([float(v) for v in eef])
    if not points:
        return None
    arr = np.asarray(points, dtype=float)
    lo, hi = arr.min(0) - pad, arr.max(0) + pad
    lo[2] = min(lo[2], -0.02)
    return lo, hi


def _grip_width(entry: dict) -> float | None:
    qpos = (entry.get("state") or {}).get("robot0_gripper_qpos")
    return sum(abs(float(v)) for v in qpos) if qpos else None


# ---------------------------------------------------------------------------
# The evidence panel: the FULL call timeline, in run order
# ---------------------------------------------------------------------------
#
# The panel is the navigator, not a per-step footnote: an env-step slider
# alone hides the story, because a perception-heavy run issues dozens of
# calls while the world sits in one state (and a step may have no stored
# world map at all). Every call is always listed; selecting one drives the
# 3D view to the nearest stored frame, and moving the slider highlights and
# scrolls to the calls issued in that state.

def _panel_entries(run: RunReplay) -> list[dict]:
    """The full message flow, flattened: text and call items in written order."""
    by_seq = {c.seq: c for c in run.calls}
    items: list[dict] = []
    for turn in run.turns:
        turn_step = next(
            (by_seq[v].step_before or 0 for k, v in turn.segments
             if k == "call" and v in by_seq), None,
        )
        first = True
        for kind, value in turn.segments:
            base = {"turn": turn.index, "new_turn": first, "turn_step": turn_step}
            first = False
            if kind == "text":
                items.append({**base, "kind": "text",
                              "html": render_markdown(str(value))})
                continue
            call = by_seq.get(value)
            if call is None:
                continue
            card = render_call(call, run)
            items.append({
                **base, "kind": "call",
                "seq": call.seq,
                "step": call.step_before if call.step_before is not None else 0,
                "title": card.title,
                "lines": card.lines,
                "advanced": call.advanced,
            })
    return items


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def build_3d_html(run: RunReplay, *, stride: int = 1, prefer_hi: bool = False) -> str | None:
    """The full 3D replay page, or None when the run stored no world maps."""
    frames_src = _frame_sources(run.run_dir, prefer_hi)
    if not frames_src:
        return None
    hits = _segment_hits(run)
    bounds = _bounds(run, hits)
    by_step_state = {e.get("step_idx"): e for e in run.states}
    trajectory = [
        (e.get("step_idx"), [float(v) for v in (e.get("state") or {})["robot0_eef_pos"]])
        for e in run.states if (e.get("state") or {}).get("robot0_eef_pos")
    ]

    plotly_frames, slider_steps = [], []
    for step, (world_path, rgb_path) in frames_src.items():
        pts, cols = _cloud(world_path, rgb_path, stride, bounds)
        colours = (["#%02x%02x%02x" % tuple(v) for v in cols]
                   if cols is not None else pts[:, 2].round(4).tolist())
        known = [h for h in hits if h["step"] <= step]
        entry = by_step_state.get(step) or {}
        cmd = entry.get("command") or {}
        target = cmd.get("xyz") or (entry.get("result") or {}).get("target_xyz")
        path = [p for s, p in trajectory if s <= step]
        now = [p for s, p in trajectory if s == step]

        data = [
            {"type": "scatter3d", "mode": "markers",
             "x": pts[:, 0].round(4).tolist(), "y": pts[:, 1].round(4).tolist(),
             "z": pts[:, 2].round(4).tolist(),
             "marker": {"size": 1.6, "color": colours, "opacity": 0.9},
             "hoverinfo": "skip", "name": "scene"},
            {"type": "scatter3d", "mode": "markers",
             "x": [h["xyz"][0] for h in known], "y": [h["xyz"][1] for h in known],
             "z": [h["xyz"][2] for h in known],
             "marker": {"size": 7, "color": "#2ca02c", "symbol": "circle-open",
                        "line": {"width": 3}},
             "text": [f"#{h['seq']} {h['entity'] or h['prompt']} "
                      f"(step {h['step']}, score {h['score']})" for h in known],
             "hoverinfo": "text", "name": "segment readings so far"},
            {"type": "scatter3d", "mode": "markers",
             "x": [float(target[0])] if target else [],
             "y": [float(target[1])] if target else [],
             "z": [float(target[2])] if target else [],
             "marker": {"size": 8, "color": "#d62728", "symbol": "x"},
             "text": [f"target of {cmd.get('action')}"] if target else [],
             "hoverinfo": "text", "name": "this step's target"},
            {"type": "scatter3d", "mode": "lines+markers",
             "x": [p[0] for p in path], "y": [p[1] for p in path],
             "z": [p[2] for p in path],
             "line": {"color": "#1f77b4", "width": 4},
             "marker": {"size": 3, "color": "#1f77b4"},
             "hoverinfo": "skip", "name": "eef path so far"},
            {"type": "scatter3d", "mode": "markers",
             "x": [p[0] for p in now], "y": [p[1] for p in now],
             "z": [p[2] for p in now],
             "marker": {"size": 9, "color": "#ff7f0e", "symbol": "diamond",
                        "line": {"color": "#333333", "width": 1}},
             "hoverinfo": "skip", "name": "eef now"},
        ]
        width = _grip_width(entry)
        action = cmd.get("action") or (entry.get("result") or {}).get("name") or "-"
        title = (f"step {step}/{max(frames_src)} &nbsp; {action} &nbsp;|&nbsp; gripper "
                 + (f"{width:.4f} m" if width is not None else "-")
                 + ("  ← CLOSED ON NOTHING" if (width is not None and width < 0.01) else "")
                 + f" &nbsp;|&nbsp; {len(pts)} pts")
        plotly_frames.append({"name": str(step), "data": data,
                              "layout": {"title": {"text": title}}})
        slider_steps.append({"label": str(step), "method": "animate",
                             "args": [[str(step)], {"mode": "immediate",
                                                    "frame": {"duration": 0, "redraw": True},
                                                    "transition": {"duration": 0}}]})

    scene = {"aspectmode": "data", "xaxis": {"title": "x (m)"},
             "yaxis": {"title": "y (m)"}, "zaxis": {"title": "z (m)"}}
    if bounds is not None:
        lo, hi = bounds
        for axis, index in (("xaxis", 0), ("yaxis", 1), ("zaxis", 2)):
            scene[axis]["range"] = [float(lo[index]), float(hi[index])]
    layout = {
        "margin": {"l": 0, "r": 0, "t": 34, "b": 0},
        "showlegend": True,
        "legend": {"orientation": "h", "y": -0.02, "font": {"size": 10}},
        "scene": scene,
        "title": {"text": plotly_frames[0]["layout"]["title"]["text"], "font": {"size": 13}},
        "uirevision": "keep",
        "sliders": [{"active": 0, "pad": {"t": 46, "l": 10},
                     "currentvalue": {"prefix": "step: ", "font": {"size": 13}},
                     "steps": slider_steps}],
        "updatemenus": [{
            "type": "buttons", "showactive": False,
            "x": 0.02, "y": 0, "xanchor": "right", "yanchor": "top",
            "pad": {"t": 60, "r": 10},
            "buttons": [
                {"label": "play", "method": "animate",
                 "args": [None, {"fromcurrent": True,
                                 "frame": {"duration": 700, "redraw": True},
                                 "transition": {"duration": 0}}]},
                {"label": "pause", "method": "animate",
                 "args": [[None], {"mode": "immediate",
                                   "frame": {"duration": 0, "redraw": False}}]},
            ]}],
    }

    status = "TERMINATED (success)" if run.terminated else "NOT TERMINATED"
    profile = (run.sandbox or {}).get("profile", "—")
    finish = run.finish or {}
    finish_line = (f" · finish: {finish.get('status')} — {finish.get('summary')}"
                   if finish else "")
    panel = _panel_entries(run)
    has_2d = (run.run_dir / "replay.html").exists()

    return _TEMPLATE % {
        "name": run.run_dir.name,
        "task": run.task_language or "(task unknown)",
        "status": status,
        "status_class": "ok" if run.terminated else "bad",
        "meta": f"model {run.model or '?'} · sandbox {profile} · "
                f"{len(run.calls)} tool calls{finish_line}",
        "link_2d": '<a href="replay.html">2D evidence timeline</a> · ' if has_2d else "",
        "frames": json.dumps(plotly_frames),
        "layout": json.dumps(layout),
        "panel": json.dumps(panel),
        "cdn": _PLOTLY_CDN,
    }


def write_3d_replay(run: RunReplay, out: Path | None = None) -> Path | None:
    html = build_3d_html(run)
    if html is None:
        return None
    out = out or (run.run_dir / "replay_3d.html")
    out.write_text(html)
    return out


_TEMPLATE = """<!doctype html><meta charset="utf-8">
<title>3D replay %(name)s</title>
<script src="%(cdn)s"></script>
<style>
body { margin:0; font:13px/1.5 system-ui,sans-serif; color:#1c2330; }
header { background:#1c2330; color:#eef1f6; padding:10px 16px; }
header .meta { font-size:11px; color:#9fb0c9; margin-top:2px; }
header a { color:#9fb0c9; }
.ok { color:#35c26a; font-weight:600; } .bad { color:#ff7a6e; font-weight:600; }
#wrap { display:flex; height:calc(100vh - 58px); }
#p { flex:1 1 auto; min-width:0; }
#side { width:430px; flex:0 0 430px; overflow-y:auto; border-left:1px solid #dde3ec;
        padding:10px 14px; background:#f6f7f9; scroll-behavior:smooth; }
.turnhead { font-size:11px; font-weight:600; color:#67718a; margin:14px 0 2px;
            text-transform:uppercase; letter-spacing:.4px; }
.call { background:#fff; border:1px solid #dde3ec; border-left:3px solid #dde3ec;
        border-radius:6px; padding:7px 10px; margin:7px 0; cursor:pointer; }
.call:hover { border-color:#b9c4de; }
.call.current { border-left-color:#ff7f0e; background:#fff9f2; }
.call .t { font-weight:600; font-size:13px; }
.call .t .seq { color:#8a94a6; font-weight:400; font-size:11px; }
.call .t .adv { background:#ffe6c9; color:#8a5200; font-size:10px;
                border-radius:4px; padding:0 5px; margin-left:6px; }
.call .t .st { float:right; font-size:10px; color:#8a94a6; }
.call ul { margin:4px 0 0; padding-left:17px; font-size:12px; color:#3c4557; }
.call li { margin:1px 0; }
.reason { border-left:3px solid #7a8cff; background:#eef0ff; padding:7px 10px;
          font-size:12px; border-radius:0 5px 5px 0; margin:8px 0 4px; color:#2c3550; }
.reason p { margin:3px 0; } .reason ul { margin:3px 0; padding-left:17px; }
.reason code, .call code { background:#e3e7f2; border-radius:3px; padding:0 3px;
                           font-size:11px; }
.call a { font-size:10px; color:#7a8cff; text-decoration:none; }
</style>
<header>
  <b>%(name)s</b> &nbsp; %(task)s &nbsp; <span class="%(status_class)s">%(status)s</span>
  <div class="meta">%(meta)s · %(link_2d)sclick a call to drive the 3D view; the slider and
  play sync back. green = segment readings known at that step, red x = motion target,
  orange = eef now.</div>
</header>
<div id="wrap">
  <div id="p"></div>
  <div id="side"><div id="calls"></div></div>
</div>
<script>
var frames = %(frames)s;
var layout = %(layout)s;
var panel = %(panel)s;
var frameSteps = frames.map(function(f) { return parseInt(f.name, 10); });

function esc(s) { return String(s).replace(/[&<>"]/g, function(c) {
  return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]; }); }

// Nearest stored frame at-or-before the step a call was issued in (a step
// with no dumped world map falls back to the closest earlier view).
function frameFor(step) {
  var best = frameSteps[0];
  frameSteps.forEach(function(s) { if (s <= step) best = s; });
  return best;
}

// Build the full message flow once: every turn's prose and calls in the
// order the model wrote them — nothing hidden, nothing reordered.
(function() {
  var out = "";
  panel.forEach(function(e) {
    if (e.new_turn) {
      out += '<div class="turnhead">turn ' + (e.turn || "?")
          + (e.turn_step !== null
             ? ' <span style="color:#a5aec2">· world @ step ' + e.turn_step + '</span>'
             : '') + '</div>';
    }
    if (e.kind === "text") {
      out += '<div class="reason">' + e.html + '</div>';
      return;
    }
    out += '<div class="call" id="pcall-' + e.seq + '" data-step="' + e.step + '">'
        + '<div class="t"><span class="seq">#' + e.seq + '</span> ' + esc(e.title)
        + (e.advanced ? '<span class="adv">env step</span>' : '')
        + ' <a href="replay.html#seq-' + e.seq + '" onclick="event.stopPropagation()">2D ↗</a>'
        + '<span class="st">@ step ' + e.step + '</span></div><ul>'
        + e.lines.map(function(l) { return '<li>' + esc(l) + '</li>'; }).join('')
        + '</ul></div>';
  });
  document.getElementById("calls").innerHTML = out;
})();

var gdRef = null, suppressScroll = false;

function highlight(frameStep, scroll) {
  var first = null;
  document.querySelectorAll(".call").forEach(function(el) {
    var on = frameFor(parseInt(el.dataset.step, 10)) === frameStep;
    el.classList.toggle("current", on);
    if (on && first === null) first = el;
  });
  if (scroll && first) first.scrollIntoView({block: "center"});
}

function goToFrame(frameStep, scroll) {
  if (gdRef) Plotly.animate(gdRef, [String(frameStep)],
      {mode: "immediate", frame: {duration: 0, redraw: true},
       transition: {duration: 0}});
  highlight(frameStep, scroll);
}

document.getElementById("calls").addEventListener("click", function(ev) {
  var el = ev.target.closest(".call");
  if (!el) return;
  suppressScroll = true;   // the user is already looking at this entry
  goToFrame(frameFor(parseInt(el.dataset.step, 10)), false);
  suppressScroll = false;
});

Plotly.newPlot("p", frames[0].data, layout).then(function(gd) {
  gdRef = gd;
  Plotly.addFrames("p", frames);
  gd.on("plotly_sliderchange", function(e) {
    highlight(parseInt(e.step.label, 10), true);
  });
  // fires per frame during play, so the panel follows the animation
  gd.on("plotly_animatingframe", function(e) {
    var name = e.name || (e.frame && e.frame.name);
    if (name !== undefined && !suppressScroll) highlight(parseInt(name, 10), true);
  });
  highlight(frameSteps[0], false);
});
</script>"""
