"""Entity databus: append-only readings, staleness, identity drift, concurrency."""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, "/Users/yanxinpeng/Desktop/Spring2026/PRAxIs/RPent")
OUT = Path(__file__).parent / "databus_run"
if OUT.exists():
    shutil.rmtree(OUT)

from rpent.utils.logging import init_output_dir  # noqa: E402

init_output_dir(OUT)

from robots.libero.tools import databus  # noqa: E402
from robots.libero.tools.artifacts import artifact_path  # noqa: E402

failures = []


def check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL':4}  {label}" + (f"\n        {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(label)


def reading(step, xyz, **kw):
    return {"step": step, "camera": "agentview", "prompt": "the woven basket",
            "score": 0.81, "world_xyz": xyz, "segment_path": f"segments/s_{step}.json",
            "world_path": f"world/world_{step:02d}.npy", **kw}


print("=== 1. register + append-only ===")
databus.append_reading(OUT, "basket_cavity", reading(0, [0.10, 0.20, 0.90]))
info = databus.append_reading(OUT, "basket_cavity", reading(3, [0.11, 0.20, 0.90]))
hist = databus.load(OUT)["basket_cavity"]
check("both readings kept, nothing overwritten", len(hist) == 2, str(len(hist)))
check("order is oldest first", [r["step"] for r in hist] == [0, 3])
check("small move reported, no identity warning",
      info["moved_since_last_m"] == 0.01 and "identity_warning" not in info, json.dumps(info))
check("provenance preserved on each reading",
      all(r.get("world_path") and r.get("segment_path") for r in hist))

print("\n=== 2. identity drift is reported, not resolved ===")
drift = databus.append_reading(OUT, "basket_cavity", reading(4, [0.30, 0.20, 0.90]))
check("large jump raises identity_warning", "identity_warning" in drift,
      json.dumps(drift))
check("the reading is still stored (harness reports, never discards)",
      len(databus.load(OUT)["basket_cavity"]) == 3)

print("\n=== 3. staleness after motion ===")
databus.append_reading(OUT, "far_plate", reading(4, [-0.40, 0.20, 0.90]))
idx = databus.index(OUT)
check("all fresh before any motion",
      all(r["stale_reason"] == databus.FRESH for r in idx["entities"].values()))

# eef travels near the basket (x .28->.32 at y .20) but far from the plate
databus.mark_after_motion(OUT, eef_before=[0.28, 0.20, 0.95],
                          eef_after=[0.32, 0.20, 0.95], gripper_open=True)
idx = databus.index(OUT)
check("entity the eef passed near -> possibly_bumped",
      idx["entities"]["basket_cavity"]["stale_reason"] == databus.POSSIBLY_BUMPED,
      idx["entities"]["basket_cavity"]["stale_reason"])
check("entity far from the motion -> unverified (not 'fresh', not 'bumped')",
      idx["entities"]["far_plate"]["stale_reason"] == databus.UNVERIFIED,
      idx["entities"]["far_plate"]["stale_reason"])
check("stale_detail carries the measured distance",
      "m " in idx["entities"]["far_plate"]["stale_detail"]
      or "m away" in idx["entities"]["far_plate"]["stale_detail"],
      idx["entities"]["far_plate"]["stale_detail"])

print("\n=== 4. closed gripper near a reading -> held ===")
databus.mark_after_motion(OUT, eef_before=[0.30, 0.20, 0.92],
                          eef_after=[0.30, 0.20, 0.92], gripper_open=False)
idx = databus.index(OUT)
check("gripper closed on it -> held", idx["entities"]["basket_cavity"]["stale_reason"] == databus.HELD,
      idx["entities"]["basket_cavity"]["stale_reason"])
check("held detail points at world_extent(mode='held_object')",
      "held_object" in idx["entities"]["basket_cavity"]["stale_detail"])
databus.mark_after_motion(OUT, eef_before=[-0.9, -0.9, 0.9],
                          eef_after=[-0.9, -0.9, 0.9], gripper_open=True)
check("held is sticky: a later far motion does not silently 'unhold' it",
      databus.index(OUT)["entities"]["basket_cavity"]["stale_reason"] == databus.HELD)

print("\n=== 4b. cross-entity collision ===")
# two DIFFERENT names on nearly the same spot -> at most one label is right
c1 = databus.append_reading(OUT, "red_bottle_a", reading(5, [0.400, 0.100, 0.900]))
check("first of a colliding pair raises nothing", "collision_warning" not in c1)
c2 = databus.append_reading(OUT, "red_bottle_b", reading(5, [0.412, 0.104, 0.900]))
check("second raises collision_warning", "collision_warning" in c2, json.dumps(c2))
check("names the other entity and the gap",
      c2.get("collision_with") == "red_bottle_a" and c2["collision_gap_m"] < 0.03,
      json.dumps(c2))
check("warning tells the planner to re-phrase, not to re-ask",
      "differently-phrased" in c2["collision_warning"])
far = databus.append_reading(OUT, "red_bottle_c", reading(5, [0.400, 0.400, 0.900]))
check("a well-separated third name does NOT collide", "collision_warning" not in far,
      json.dumps(far))
check("collision does not suppress storage", len(databus.load(OUT)["red_bottle_b"]) == 1)

print("\n=== 5. index shape ===")
idx = databus.index(OUT)
row = idx["entities"]["far_plate"]
check("index reports latest reading + count, not the whole history",
      set(row) == {"world_xyz", "step", "camera", "prompt", "score", "stale_reason",
                   "stale_detail", "segment_path", "n_readings"}, str(sorted(row)))
check("index is None when nothing registered", databus.index(OUT / "nonexistent") is None)
check("index carries a note telling the planner to re-segment stale readings",
      "re-segment" in idx["note"])

print("\n=== 6. concurrent appends (a turn's tool calls run in threads) ===")
import threading  # noqa: E402

shutil.rmtree(artifact_path(OUT, "entities").parent, ignore_errors=True)
threads = [threading.Thread(target=databus.append_reading,
                            args=(OUT, f"e{i%3}", reading(i, [0.1 * i, 0.2, 0.9])))
           for i in range(30)]
for t in threads:
    t.start()
for t in threads:
    t.join()
loaded = databus.load(OUT)
total = sum(len(v) for v in loaded.values())
check("no appends lost under 30 concurrent writers", total == 30, f"kept {total}/30")
check("file is valid JSON afterwards",
      isinstance(json.loads(artifact_path(OUT, "entities").read_text()), dict))

print("\n=== 7. path lands in the derived partition ===")
p = artifact_path(OUT, "entities")
check("entities.json lives under analysis/", p.parent.name == "analysis", str(p))

print()
if failures:
    print(f"{len(failures)} CHECK(S) FAILED")
    sys.exit(1)
print("all checks passed")
