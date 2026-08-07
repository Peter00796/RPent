#!/usr/bin/env python3
"""Interactive 3D replay of an RPent episode: a slider over the whole run.

Every executed command leaves a world map (per-pixel world XYZ) and a matching
RGB frame, so each step is already a coloured point cloud — no reconstruction.
This stitches them into one HTML with a step slider and a play button, and
overlays the agent's reasoning as it accumulates:

  scene cloud        the world map at the selected step, in true colour
  SAM3 answers       every segment call made at or before this step, so you
                     watch the agent's belief about the scene build up
  motion target      the xyz the current command was asked to reach
  eef path           the trajectory up to this step, current pose highlighted

Gripper width is printed in each frame's title, so a close onto empty air
(width under 1cm) is visible at the moment it happens.

Full resolution by default: 256x256 maps give ~65k points per frame, which is
24 frames x 65k = fine for one file. The hi-res 1024x1024 maps only exist for
the last few steps, so --hi uses them where available.

Usage:
  python replay_run_3d.py <run_dir>                       # -> replay_3d.html
  python replay_run_3d.py <run_dir> --out replay.html
  python replay_run_3d.py <run_dir> --stride 2            # lighter file
  python replay_run_3d.py <run_dir> --hi                  # prefer 1024 maps
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import numpy as np


def load_states(run_dir):
    p = os.path.join(run_dir, "states.json")
    if not os.path.exists(p):
        return []
    try:
        return [e for e in json.load(open(p)) if isinstance(e, dict)]
    except Exception:
        return []


def load_segments(run_dir):
    out = []
    for p in sorted(glob.glob(os.path.join(run_dir, "segments", "segment_*.json"))):
        try:
            d = json.load(open(p))
        except Exception:
            continue
        if d.get("error") or not d.get("world_xyz"):
            continue
        d["file"] = os.path.basename(p)
        out.append(d)
    return out


def frame_sources(run_dir, prefer_hi):
    """step -> (world npy path, rgb png path or None), for every step with a map."""
    order = (("world_hi", "images_cam_hi"), ("world", "images_cam"))
    if not prefer_hi:
        order = order[::-1]
    frames = {}
    for sub, img_sub in order:
        for f in sorted(glob.glob(os.path.join(run_dir, sub, "*.npy"))):
            n = os.path.basename(f).rsplit("_", 1)[1].split(".")[0]
            step = int(n)
            if step in frames:
                continue                      # first source in `order` wins
            rgbs = glob.glob(os.path.join(run_dir, img_sub, "*%s.png" % n))
            frames[step] = (f, rgbs[0] if rgbs else None)
    return dict(sorted(frames.items()))


def cloud(world_path, rgb_path, stride, bounds):
    w = np.load(world_path).astype(np.float32)[::stride, ::stride]
    pts = w.reshape(-1, 3)
    ok = np.isfinite(pts).all(1) & (np.abs(pts).sum(1) > 0)
    cols = None
    if rgb_path:
        from PIL import Image
        im = Image.open(rgb_path).convert("RGB")
        a = np.asarray(im)
        if a.shape[0] == np.load(world_path).shape[0]:
            cols = (a[::stride, ::stride].reshape(-1, 3))[ok]
    pts = pts[ok]
    if bounds is not None:
        lo, hi = bounds
        m = np.all((pts >= lo) & (pts <= hi), axis=1)
        pts = pts[m]
        cols = cols[m] if cols is not None else None
    return pts, cols


def workspace_bounds(segs, states, pad=0.18):
    P = [[float(v) for v in s["world_xyz"]] for s in segs]
    for e in states:
        cmd = e.get("command") or {}
        t = cmd.get("xyz") or (e.get("result") or {}).get("target_xyz")
        if t:
            P.append([float(v) for v in t])
        st = e.get("state") or {}
        if st.get("robot0_eef_pos"):
            P.append([float(v) for v in st["robot0_eef_pos"]])
    if not P:
        return None
    A = np.array(P, float)
    lo, hi = A.min(0) - pad, A.max(0) + pad
    lo[2] = min(lo[2], -0.02)
    return lo, hi


def grip_width(e):
    q = (e.get("state") or {}).get("robot0_gripper_qpos")
    return sum(abs(float(v)) for v in q) if q else None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir")
    ap.add_argument("--out", default=None, help="output html (default <run_dir>/replay_3d.html)")
    ap.add_argument("--stride", type=int, default=1,
                    help="world-map subsample stride (1 = full resolution)")
    ap.add_argument("--hi", action="store_true",
                    help="prefer the 1024x1024 maps where they exist")
    a = ap.parse_args()

    R = a.run_dir.rstrip("/")
    states = load_states(R)
    segs = load_segments(R)
    frames = frame_sources(R, a.hi)
    if not frames:
        print("no world maps under " + R, file=sys.stderr)
        return 1
    bounds = workspace_bounds(segs, states)
    by_step = {e.get("step_idx"): e for e in states}

    goal = states[0].get("task_language") if states else "?"
    term = any(e.get("libero_terminated") or (e.get("result") or {}).get("libero_terminated")
               for e in states)

    # Trajectory in execution order, so a frame can show the path so far.
    traj = [(e.get("step_idx"), [float(v) for v in (e.get("state") or {})["robot0_eef_pos"]])
            for e in states if (e.get("state") or {}).get("robot0_eef_pos")]

    plotly_frames, slider_steps = [], []
    total_pts = 0
    for step, (wp, ip) in frames.items():
        pts, cols = cloud(wp, ip, a.stride, bounds)
        total_pts += len(pts)
        colours = (["#%02x%02x%02x" % tuple(v) for v in cols]
                   if cols is not None else pts[:, 2].round(4).tolist())

        # SAM3 answers known at this step: the agent's belief so far.
        known = [s for s in segs if (s.get("source_step") or 0) <= step]
        e = by_step.get(step) or {}
        cmd = e.get("command") or {}
        tgt = cmd.get("xyz") or (e.get("result") or {}).get("target_xyz")
        path = [p for st, p in traj if st <= step]
        cur = [p for st, p in traj if st == step]

        data = [
            {"type": "scatter3d", "mode": "markers",
             "x": pts[:, 0].round(4).tolist(), "y": pts[:, 1].round(4).tolist(),
             "z": pts[:, 2].round(4).tolist(),
             "marker": {"size": 1.6, "color": colours, "opacity": 0.9},
             "hoverinfo": "skip", "name": "scene"},
            {"type": "scatter3d", "mode": "markers",
             "x": [float(s["world_xyz"][0]) for s in known],
             "y": [float(s["world_xyz"][1]) for s in known],
             "z": [float(s["world_xyz"][2]) for s in known],
             "marker": {"size": 7, "color": "#2ca02c", "symbol": "circle-open",
                        "line": {"width": 3}},
             "text": ["step %s | %.3f | %s" % (s.get("source_step"), s.get("score") or 0,
                                               str(s.get("prompt"))[:44]) for s in known],
             "hoverinfo": "text", "name": "SAM3 answers so far"},
            {"type": "scatter3d", "mode": "markers",
             "x": [float(tgt[0])] if tgt else [], "y": [float(tgt[1])] if tgt else [],
             "z": [float(tgt[2])] if tgt else [],
             "marker": {"size": 8, "color": "#d62728", "symbol": "x"},
             "text": ["target of %s" % cmd.get("action")] if tgt else [],
             "hoverinfo": "text", "name": "this step's target"},
            {"type": "scatter3d", "mode": "lines+markers",
             "x": [p[0] for p in path], "y": [p[1] for p in path],
             "z": [p[2] for p in path],
             "line": {"color": "#1f77b4", "width": 4},
             "marker": {"size": 3, "color": "#1f77b4"},
             "hoverinfo": "skip", "name": "eef path so far"},
            {"type": "scatter3d", "mode": "markers",
             "x": [p[0] for p in cur], "y": [p[1] for p in cur], "z": [p[2] for p in cur],
             "marker": {"size": 9, "color": "#ff7f0e", "symbol": "diamond",
                        "line": {"color": "#333333", "width": 1}},
             "hoverinfo": "skip", "name": "eef now"},
        ]
        gw = grip_width(e)
        act = cmd.get("action") or (e.get("result") or {}).get("name") or "-"
        dist = (e.get("result") or {}).get("final_dist_m")
        title = "step %d/%d &nbsp; %s &nbsp;|&nbsp; gripper %s%s &nbsp;|&nbsp; %d pts" % (
            step, max(frames), act,
            ("%.4f m" % gw) if gw is not None else "-",
            "  ← CLOSED ON NOTHING" if (gw is not None and gw < 0.01) else "",
            len(pts))
        if isinstance(dist, (int, float)):
            title += " &nbsp;|&nbsp; reach err %.4f m" % dist
        plotly_frames.append({"name": str(step), "data": data,
                              "layout": {"title": {"text": title}}})
        slider_steps.append({
            "label": str(step), "method": "animate",
            "args": [[str(step)], {"mode": "immediate",
                                   "frame": {"duration": 0, "redraw": True},
                                   "transition": {"duration": 0}}]})

    out = a.out or os.path.join(R, "replay_3d.html")
    lo, hi = bounds if bounds else (None, None)
    scene = {"aspectmode": "data",
             "xaxis": {"title": "x (m)"}, "yaxis": {"title": "y (m)"},
             "zaxis": {"title": "z (m)"}}
    if bounds is not None:
        scene["xaxis"]["range"] = [float(lo[0]), float(hi[0])]
        scene["yaxis"]["range"] = [float(lo[1]), float(hi[1])]
        scene["zaxis"]["range"] = [float(lo[2]), float(hi[2])]

    layout = {
        "margin": {"l": 0, "r": 0, "t": 34, "b": 0},
        "showlegend": True,
        "legend": {"orientation": "h", "y": -0.02, "font": {"size": 10}},
        "scene": scene,
        "title": {"text": plotly_frames[0]["layout"]["title"]["text"],
                  "font": {"size": 13}},
        "uirevision": "keep",           # keep the camera when the slider moves
        "sliders": [{
            "active": 0, "pad": {"t": 46, "l": 10},
            "currentvalue": {"prefix": "step: ", "font": {"size": 13}},
            "steps": slider_steps,
        }],
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
            ],
        }],
    }

    html = """<!doctype html><meta charset="utf-8">
<title>replay %s</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<body style="margin:0;font-family:system-ui,sans-serif;background:#fff">
<div style="padding:6px 12px;font-size:13px">
  <b>%s</b> &nbsp;|&nbsp; %s &nbsp;|&nbsp; <b>%s</b>
  <span style="font-size:11px;color:#555">&nbsp; drag the slider or press play.
  green = SAM3 answers known at that step (hover for prompt/score),
  red x = that step's motion target, orange diamond = end-effector now.</span>
</div>
<div id="p" style="width:100vw;height:90vh"></div>
<script>
var frames = %s;
Plotly.newPlot("p", frames[0].data, %s).then(function(){
  Plotly.addFrames("p", frames);
});
</script>""" % (os.path.basename(R), os.path.basename(R), goal,
                "SUCCESS" if term else "FAILED",
                json.dumps(plotly_frames), json.dumps(layout))
    open(out, "w").write(html)
    print("wrote %s (%.1f MB, %d frames, %d points total)" % (
        out, os.path.getsize(out) / 1e6, len(plotly_frames), total_pts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
