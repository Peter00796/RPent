"""_principal_axes against synthetic clouds whose true axes are known."""
import sys

import numpy as np

sys.path.insert(0, "/Users/yanxinpeng/Desktop/Spring2026/PRAxIs/RPent")
from robots.libero.tools.geometry import _mask_to_world, _principal_axes  # noqa: E402

rng = np.random.default_rng(0)
failures = []


def check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL':4}  {label}" + (f"\n        {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(label)


def box_cloud(length, width, height, yaw_deg, n=4000, centre=(0.1, 0.2, 0.9)):
    """Points filling a box of given dims, rotated by yaw about world z."""
    p = np.stack([
        rng.uniform(-length / 2, length / 2, n),
        rng.uniform(-width / 2, width / 2, n),
        rng.uniform(-height / 2, height / 2, n),
    ], axis=1)
    a = np.radians(yaw_deg)
    R = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    return p @ R.T + np.asarray(centre)


def fold(deg):
    while deg >= 90:
        deg -= 180
    while deg < -90:
        deg += 180
    return deg


print("=== 1. long axis yaw recovered across the full range ===")
worst = 0.0
for true_yaw in (-80, -45, -10, 0, 15, 30, 60, 89):
    s = _principal_axes(box_cloud(0.20, 0.05, 0.05, true_yaw))
    got = s["footprint"]["long_axis_yaw_deg"]
    err = abs(fold(got - true_yaw))
    worst = max(worst, err)
    if err > 2.0:
        print(f"        yaw {true_yaw}: got {got} (err {err:.1f})")
check(f"long_axis_yaw within 2 deg at 8 angles (worst {worst:.2f})", worst <= 2.0)

print("\n=== 2. short axis is perpendicular, and is the graspable width ===")
s = _principal_axes(box_cloud(0.20, 0.05, 0.05, 30))
gap = abs(fold(s["footprint"]["short_axis_yaw_deg"] - s["footprint"]["long_axis_yaw_deg"]))
check("short axis is 90 deg from long", abs(gap - 90) < 2.0, f"gap={gap:.2f}")
check("long_extent ~ 0.20", abs(s["footprint"]["long_extent_m"] - 0.20) < 0.01,
      str(s["footprint"]["long_extent_m"]))
check("short_extent ~ 0.05", abs(s["footprint"]["short_extent_m"] - 0.05) < 0.01,
      str(s["footprint"]["short_extent_m"]))
check("graspable_width_m == short_extent_m (the span the fingers must cover)",
      s["graspable_width_m"] == s["footprint"]["short_extent_m"])

print("\n=== 3. axis-aligned bbox vs fitted box on a 45-degree object ===")
pts = box_cloud(0.20, 0.05, 0.05, 45)
aabb = [pts[:, i].max() - pts[:, i].min() for i in range(3)]
s = _principal_axes(pts)
check("AABB is misleading: both xy extents inflated ~0.18",
      aabb[0] > 0.15 and aabb[1] > 0.15, f"aabb={[round(v,3) for v in aabb]}")
check("fitted box recovers the true 0.20 x 0.05 footprint",
      abs(s["footprint"]["long_extent_m"] - 0.20) < 0.01
      and abs(s["footprint"]["short_extent_m"] - 0.05) < 0.01,
      f"{s['footprint']['long_extent_m']} x {s['footprint']['short_extent_m']}")

print("\n=== 4. degeneracy is reported, not invented ===")
round_s = _principal_axes(box_cloud(0.09, 0.085, 0.10, 0))  # near-square footprint
check("near-round footprint -> yaw_is_meaningful False",
      round_s["footprint"]["yaw_is_meaningful"] is False,
      str(round_s["footprint"]))
elong = _principal_axes(box_cloud(0.20, 0.05, 0.05, 0))
check("elongated footprint -> yaw_is_meaningful True",
      elong["footprint"]["yaw_is_meaningful"] is True)

print("\n=== 5. orientation classification ===")
cases = [("upright bottle 0.05x0.05x0.20", box_cloud(0.05, 0.05, 0.20, 0), "upright"),
         ("toppled bottle 0.20x0.05x0.05", box_cloud(0.20, 0.05, 0.05, 0), "lying"),
         ("cube-ish 0.09x0.09x0.09", box_cloud(0.09, 0.09, 0.09, 0), "ambiguous")]
for label, cloud, want in cases:
    got = _principal_axes(cloud)["orientation"]
    check(f"{label} -> {want}", got == want, f"got {got}")

print("\n=== 6. planar detection (a plate top) ===")
plate = box_cloud(0.18, 0.18, 0.001, 0)
check("thin slab -> planar True", _principal_axes(plate)["planar"] is True)
check("thick body -> planar False", _principal_axes(box_cloud(0.1, 0.1, 0.08, 0))["planar"] is False)

print("\n=== 7. guards ===")
check("too few points -> None", _principal_axes(box_cloud(0.2, 0.05, 0.05, 0, n=5)) is None)
check("all points identical -> None (no axis to fit)",
      _principal_axes(np.tile([0.1, 0.2, 0.9], (50, 1))) is None)

print("\n=== 8. reaches segment's reply through _mask_to_world ===")
H = W = 60
world = np.zeros((H, W, 3), dtype=np.float32)
cloud = box_cloud(0.20, 0.05, 0.05, 25, n=H * W)
world[:] = cloud.reshape(H, W, 3)
mask = np.ones((H, W), dtype=bool)
out = _mask_to_world(mask, world)
check("_mask_to_world includes 'shape'", "shape" in out, str(sorted(out)))
check("its yaw matches the synthetic 25 deg",
      abs(fold(out["shape"]["footprint"]["long_axis_yaw_deg"] - 25)) < 2.0,
      str(out["shape"]["footprint"]["long_axis_yaw_deg"]))
check("bbox_3d still present (nothing replaced)", "bbox_3d" in out)

print()
if failures:
    print(f"{len(failures)} CHECK(S) FAILED")
    sys.exit(1)
print("all checks passed")
