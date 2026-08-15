"""_plan_grasp_from_points against synthetic clouds with known answers.

Scenes mirror the measured failure cases: a moka-pot-like body whose span
exceeds the jaw (ungraspable) with and without a handle bar (the bar is the
only candidate), and a book-like slab (plainly graspable). No artifacts, no
GPU: the pure function is exercised directly.
"""
import sys

import numpy as np

sys.path.insert(0, ".")
from robots.libero.tools.geometry import _plan_grasp_from_points  # noqa: E402

rng = np.random.default_rng(7)
failures = []


def check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL':4}  {label}"
          + (f"\n        {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(label)


def cylinder_shell(radius, z0, z1, n=6000, centre=(0.0, 0.0)):
    phi = rng.uniform(0, 2 * np.pi, n)
    z = rng.uniform(z0, z1, n)
    return np.stack([centre[0] + radius * np.cos(phi),
                     centre[1] + radius * np.sin(phi), z], axis=1)


def box_fill(x0, x1, y0, y1, z0, z1, n=1500):
    return np.stack([rng.uniform(x0, x1, n), rng.uniform(y0, y1, n),
                     rng.uniform(z0, z1, n)], axis=1)


# -- scene 1: pot body alone — span 0.078 exceeds the 0.072 jaw --------------
body = cylinder_shell(0.039, 0.90, 1.03)
res = _plan_grasp_from_points(body)
check("pot body alone is ungraspable", res.get("no_feasible_grasp") is True,
      f"got candidates: {res.get('candidates')}")
narrow = res.get("narrowest_span_found")
check("narrowest span reported near the true diameter",
      narrow is not None and 0.066 <= narrow <= 0.09,
      f"narrowest_span_found={narrow}")

# -- scene 2: same body + handle bar above the shoulder — bar is the answer --
bar = box_fill(-0.008, 0.008, -0.095, -0.030, 1.036, 1.050)
pot = np.vstack([body, bar])
res = _plan_grasp_from_points(pot)
cands = res.get("candidates") or []
check("handle bar yields candidates", len(cands) > 0, f"result: {res}")
if cands:
    top = cands[0]
    check("top candidate sits on the handle side",
          top["center_xyz"][1] < -0.025, f"top={top}")
    check("top candidate width fits the bar",
          top["expected_width"] <= 0.05, f"top={top}")
    check("top candidate band is at the bar height",
          top["band_z"][1] >= 1.03, f"top={top}")

# -- scene 3: book slab — plainly graspable across its thin axis -------------
book = box_fill(-0.02, 0.02, -0.075, 0.075, 0.90, 1.04, n=4000)
res = _plan_grasp_from_points(book)
cands = res.get("candidates") or []
check("book slab yields candidates", len(cands) > 0, f"result: {res}")
if cands:
    top = cands[0]
    yaw = top["close_axis_yaw_world"]
    check("book close axis is across the thin dimension",
          yaw < 0.35 or yaw > np.pi - 0.35, f"yaw={yaw}")
    check("book width near the slab thickness",
          0.028 <= top["expected_width"] <= 0.055, f"top={top}")

# -- scene 4: determinism ----------------------------------------------------
r1 = _plan_grasp_from_points(pot)
r2 = _plan_grasp_from_points(pot)
check("same cloud, same candidates", r1 == r2)

# -- scene 5: too few points is an error, not a guess ------------------------
res = _plan_grasp_from_points(pot[:10])
check("sparse cloud returns an error", "error" in res, f"result: {res}")

print()
if failures:
    print(f"FAILURES: {failures}")
    sys.exit(1)
print("OK — plan_grasp synthesis: ungraspable body, handle bar, slab, "
      "determinism, sparse guard")
