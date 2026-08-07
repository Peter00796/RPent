"""Run the new geometry tools over real pre-refactor runs.

Every reading is recomputed from the stored point cloud, so nothing here trusts a
number the old code wrote. Masks are recovered from the saved overlays: the
overlay blended masked pixels as 0.55*original + 0.45*red, so pixels that differ
from the source image are exactly the mask (pure-red source pixels are the one
blind spot, and they are counted).
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import imageio.v2 as imageio
import numpy as np

REPO = "/Users/yanxinpeng/Desktop/Spring2026/PRAxIs/RPent"
sys.path.insert(0, REPO)
DATA = Path(__file__).parent / "realdata"

import rpent.utils.logging as rlog  # noqa: E402

rlog._output_dir = DATA  # placeholder; set per run below
from robots.libero.tools.geometry import (  # noqa: E402
    _mask_to_world,
    compare_extent,
    world_extent,
)


def use_run(run_dir: Path) -> None:
    """Point the tools' get_output_dir() at this historical run."""
    rlog._output_dir = run_dir


def local(remote_path: str, run_dir: Path) -> Path:
    """Remap a recorded absolute path from the training box onto this copy."""
    parts = Path(remote_path).parts
    return run_dir.joinpath(*parts[-2:])


def recover_mask(overlay: Path, source: Path) -> tuple[np.ndarray | None, int]:
    """Recover the segmentation mask by diffing overlay against source image."""
    try:
        ov = np.asarray(imageio.imread(overlay))[..., :3].astype(np.int16)
        src = np.asarray(imageio.imread(source))[..., :3].astype(np.int16)
    except Exception:
        return None, 0
    if ov.shape != src.shape:
        return None, 0
    mask = (ov != src).any(axis=2)
    # Pure red source pixels blend to themselves and are invisible to the diff.
    blind = int(((src[..., 0] > 250) & (src[..., 1] < 5) & (src[..., 2] < 5)).sum())
    return mask, blind


runs = sorted(p.parent for p in DATA.glob("*/states.json"))
print(f"runs: {len(runs)}\n")

# ---------------------------------------------------------------------------
print("=" * 78)
print("A. WHAT THE PLANNER WAS DENIED — world_xyz vs the fitted drop point")
print("=" * 78)
print("Recomputed from each stored cloud. `gap` is the distance from world_xyz")
print("(the only number the old reply carried) to rim.xy_bbox_center (the")
print("opening's fitted centre), in the xy plane.\n")

rows = []
skipped = defaultdict(int)
blind_total = 0
for run in runs:
    use_run(run)
    for seg_file in sorted(run.glob("segments/segment_[0-9]*.json")):
        try:
            seg = json.load(seg_file.open())
        except Exception:
            skipped["unreadable json"] += 1
            continue
        if not seg.get("found") or not seg.get("world_xyz"):
            skipped["no mask found"] += 1
            continue
        wp = seg.get("world_path")
        if not wp:
            skipped["no world_path recorded"] += 1
            continue
        world_file = local(wp, run)
        if not world_file.exists():
            skipped["world map pruned from disk"] += 1
            continue
        overlay = seg_file.parent / seg_file.name.replace("segment_", "segment_overlay_").replace(".json", ".png")
        source = local(seg["image_path"], run)
        if not (overlay.exists() and source.exists()):
            skipped["overlay or source image missing"] += 1
            continue
        mask, blind = recover_mask(overlay, source)
        blind_total += blind
        if mask is None or mask.sum() < 10:
            skipped["mask unrecoverable"] += 1
            continue
        world = np.load(world_file)
        if mask.shape != world.shape[:2]:
            skipped["mask/world shape mismatch"] += 1
            continue
        fresh = _mask_to_world(mask, world)
        if not fresh.get("world_xyz"):
            skipped["recompute produced no xyz"] += 1
            continue
        rows.append({
            "run": run.name,
            "seg": seg_file.name,
            "prompt": (seg.get("prompt") or f"point{seg.get('point')}")[:38],
            "score": seg.get("score"),
            "n_pixels": fresh.get("n_pixels"),
            "old_xyz": seg["world_xyz"],
            "new_xyz": fresh["world_xyz"],
            "fresh": fresh,
            "hist_hollow": seg.get("looks_hollow"),
        })

print(f"recomputed {len(rows)} readings; skipped: {dict(skipped)}")
if blind_total:
    print(f"(mask-diff blind spot: {blind_total} pure-red source pixels across all images)")

recompute_err = [
    float(np.linalg.norm(np.asarray(r["new_xyz"]) - np.asarray(r["old_xyz"])))
    for r in rows
]
if recompute_err:
    print(f"\nsanity — recomputed world_xyz vs the stored one: "
          f"median {np.median(recompute_err)*1000:.2f} mm, "
          f"max {max(recompute_err)*1000:.2f} mm")
    print("(agreement here is what licenses trusting the recovered masks)")

gaps = []
print(f"\n{'prompt':40s} {'hollow':7s} {'n_pix':>6s} {'gap_xy_mm':>10s} {'retreat':>8s}")
print("-" * 78)
for r in rows:
    rim = r["fresh"].get("rim")
    if not rim or "xy_bbox_center" not in rim:
        continue
    gap = float(np.linalg.norm(
        np.asarray(rim["xy_bbox_center"]) - np.asarray(r["new_xyz"][:2])))
    gaps.append((gap, r))
    print(f"{r['prompt']:40s} {str(r['fresh'].get('looks_hollow')):7s} "
          f"{r['n_pixels']:>6d} {gap*1000:>10.1f} {rim.get('retreat_direction','-'):>8s}")
if gaps:
    g = np.array([x[0] for x in gaps])
    print(f"\n{len(g)} readings with a fitted rim: gap median {np.median(g)*1000:.1f} mm, "
          f"p90 {np.percentile(g,90)*1000:.1f} mm, max {g.max()*1000:.1f} mm")
    hollow = [x[1] for x in gaps if x[1]["fresh"].get("looks_hollow")]
    if hollow:
        gh = np.array([float(np.linalg.norm(
            np.asarray(r["fresh"]["rim"]["xy_bbox_center"]) - np.asarray(r["new_xyz"][:2])))
            for r in hollow])
        print(f"  of those, {len(hollow)} read as HOLLOW (containers): "
              f"gap median {np.median(gh)*1000:.1f} mm, max {gh.max()*1000:.1f} mm")

# ---------------------------------------------------------------------------
print("\n" + "=" * 78)
print("B. NEW INFORMATION — `shape` on real masks (never computed before)")
print("=" * 78)
print(f"\n{'prompt':34s} {'orient':10s} {'long':>6s} {'short':>6s} {'yaw':>7s} "
      f"{'aspect':>7s} {'yaw_ok':>6s}")
print("-" * 78)
shape_rows = [r for r in rows if r["fresh"].get("shape")]
for r in shape_rows:
    s = r["fresh"]["shape"]
    f = s["footprint"]
    print(f"{r['prompt']:34s} {s['orientation']:10s} {f['long_extent_m']:>6.3f} "
          f"{f['short_extent_m']:>6.3f} {f['long_axis_yaw_deg']:>7.1f} "
          f"{f['aspect_short_over_long']:>7.3f} {str(f['yaw_is_meaningful']):>6s}")
if shape_rows:
    widths = np.array([r["fresh"]["shape"]["graspable_width_m"] for r in shape_rows])
    meaningful = sum(1 for r in shape_rows
                     if r["fresh"]["shape"]["footprint"]["yaw_is_meaningful"])
    print(f"\n{len(shape_rows)} shapes: graspable width median {widths.mean():.3f} m "
          f"(min {widths.min():.3f}, max {widths.max():.3f})")
    print(f"  yaw meaningful for {meaningful}/{len(shape_rows)} "
          f"— the rest are near-round, where any yaw is as good as another")
    orient = defaultdict(int)
    for r in shape_rows:
        orient[r["fresh"]["shape"]["orientation"]] += 1
    print(f"  orientation: {dict(orient)}")
    # Does the fitted box disagree with the axis-aligned one?
    infl = []
    for r in shape_rows:
        aabb = r["fresh"]["bbox_3d"]["extent"]
        long_aabb = max(aabb[0], aabb[1])
        infl.append(long_aabb / r["fresh"]["shape"]["footprint"]["long_extent_m"])
    infl = np.array(infl)
    print(f"  axis-aligned xy extent / fitted long extent: median {np.median(infl):.2f}x, "
          f"max {infl.max():.2f}x  <- how much bbox_3d overstates size")

# ---------------------------------------------------------------------------
print("\n" + "=" * 78)
print("C. world_extent(mode='held_object') at steps where the gripper was closed")
print("=" * 78)
print(f"\n{'run':34s} {'step':>4s} {'grip':>6s} {'held':>5s} {'n_pts':>6s} "
      f"{'offset_xy_mm':>14s}")
print("-" * 78)
held_offsets = defaultdict(list)
for run in runs:
    use_run(run)
    states = json.load((run / "states.json").open())
    for entry in states:
        st = entry.get("state") or {}
        q = st.get("robot0_gripper_qpos")
        if not q or len(q) < 2:
            continue
        width = abs(float(q[0])) + abs(float(q[1]))
        if width > 0.06:
            continue
        nn = entry["step_idx"]
        out = world_extent(step=nn, mode="held_object")
        if out.get("error"):
            continue
        off = out.get("offset_from_eef")
        off_mm = (f"[{off[0]*1000:+.0f},{off[1]*1000:+.0f}]" if off else "-")
        print(f"{run.name[:34]:34s} {nn:>4d} {width:>6.3f} "
              f"{str(out.get('holding')):>5s} {out.get('n_points',0):>6d} {off_mm:>14s}")
        if off:
            held_offsets[run.name].append(float(np.linalg.norm(off)))
if held_offsets:
    print("\nper-run spread of the held-object offset magnitude:")
    for name, vals in held_offsets.items():
        v = np.array(vals) * 100
        print(f"  {name[:44]:44s} n={len(v):2d}  {v.min():.1f}-{v.max():.1f} cm "
              f"(spread {v.max()-v.min():.1f} cm)")
    print("  <- a spread inside one run is what rules out a fixed constant")

# ---------------------------------------------------------------------------
print("\n" + "=" * 78)
print("D. compare_extent — can it verify an outcome without segmentation?")
print("=" * 78)
for run in runs:
    use_run(run)
    states = json.load((run / "states.json").open())
    last = states[-1]["step_idx"]
    terminated = [e["step_idx"] for e in states if e.get("libero_terminated")]
    # Box the basket from whatever basket reading this run happens to hold.
    basket = None
    for seg_file in sorted(run.glob("segments/segment_[0-9]*.json")):
        try:
            seg = json.load(seg_file.open())
        except Exception:
            continue
        if seg.get("found") and seg.get("world_xyz") and "basket" in (seg.get("prompt") or ""):
            basket = seg
            break
    print(f"\n{run.name}   steps 0..{last}  "
          f"{'SOLVED at ' + str(terminated[0]) if terminated else 'NEVER TERMINATED'}")
    if basket is None:
        print("   (no basket segment in this run — skipping the container box)")
        continue
    bx, by, bz = basket["world_xyz"]
    box = dict(x_range=[bx - 0.08, bx + 0.08], y_range=[by - 0.08, by + 0.08],
               z_range=[max(0.012, bz - 0.02), bz + 0.18])
    out = compare_extent(step_a=0, step_b=last, **box)
    if out.get("error"):
        print("   error:", out["error"])
        continue
    d = out["delta"]
    a, b = out[f"step_0"], out[f"step_{last}"]
    print(f"   basket box around {[round(v,3) for v in basket['world_xyz']]}")
    print(f"   step 0    : {a['n_points_in_box']:6d} pts, {a['occupied_voxels']:4d} voxels")
    print(f"   step {last:<4d}: {b['n_points_in_box']:6d} pts, {b['occupied_voxels']:4d} voxels")
    print(f"   delta     : +{d['voxels_added']} / -{d['voxels_removed']} "
          f"(net {d['occupied_voxels_net']:+d}, iou {d['iou']})")
    if d.get("centroid_shift_m") is not None:
        print(f"   centroid shifted {d['centroid_shift_m']*1000:.0f} mm "
              f"{[round(v,3) for v in d['centroid_shift']]}")
    if d.get("added_centroid"):
        print(f"   new material centred at {d['added_centroid']}")

print("\ndone")
