"""Smoke test for the LocateAnything server: parser, then a live round-trip.

Two parts, deliberately separable:

1. **Parser checks run anywhere** -- no torch, no CUDA, no weights. They pin the
   coordinate convention, which is the part that is silently wrong if misread:
   the model emits ``<box><x1><x2><y1><y2></box>`` (both x before both y), and a
   transposed reading produces plausible-looking boxes that are simply wrong.
2. **Live check runs only with a served model** (``--endpoint``), against a real
   LIBERO agentview frame, and asserts the returned pixel coordinates land
   inside the image and index the run's world map.

Usage::

    python tests/harness/test_locateanything.py                     # parser only
    python tests/harness/test_locateanything.py --endpoint http://127.0.0.1:8115 \
        --image logs/<run>/images_cam/cam_00.png --query "bottle</c>basket"
"""

import argparse
import sys

sys.path.insert(0, ".")

from robots.libero.locateanything_server import parse_response  # noqa: E402

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)
        print(f"FAIL {msg}")
    else:
        print(f"PASS {msg}")


# --- 1. coordinate convention -------------------------------------------------
# A box occupying the left half, top quarter of a 1000x500 image.
# Token order is x1, x2, y1, y2 -> x in [0, 500], y in [0, 125].
W, H = 1000, 500
text = "bottle<box><0><500><0><250></box>"
inst, labels = parse_response(text, W, H)

check(len(inst) == 1, f"one box parsed (got {len(inst)})")
if inst:
    x1, y1, x2, y2 = inst[0]["box"]
    check(abs(x1 - 0.0) < 1e-6 and abs(x2 - 500.0) < 1e-6,
          f"x spans 0..500 px, i.e. tokens 1-2 are x (got {x1:.1f}..{x2:.1f})")
    check(abs(y1 - 0.0) < 1e-6 and abs(y2 - 125.0) < 1e-6,
          f"y spans 0..125 px, i.e. tokens 3-4 are y (got {y1:.1f}..{y2:.1f})")
    check(inst[0]["label"] == "bottle", f"label carried (got {inst[0]['label']!r})")
    cx, cy = inst[0]["center"]
    check(abs(cx - 250.0) < 1e-6 and abs(cy - 62.5) < 1e-6,
          f"centre is box midpoint (got {cx:.1f},{cy:.1f})")

# A transposed reading would give x 0..500 -> y 0..250; assert we are NOT that.
if inst:
    check(inst[0]["box"][3] != 250.0,
          "y2 is not 250 px -- guards against reading tokens as x1,y1,x2,y2")

# --- 2. multiple instances for one query --------------------------------------
multi = "bottle<box><0><100><0><100></box><box><200><300><200><300></box>"
inst, labels = parse_response(multi, W, H)
check(len(inst) == 2, f"two instances for one label (got {len(inst)})")
check(all(i["label"] == "bottle" for i in inst), "label carries forward to both")

# --- 3. explicit no-detection -------------------------------------------------
inst, labels = parse_response("teapot<box>none</box>", W, H)
check(len(inst) == 0, f"<box>none</box> yields no instance (got {len(inst)})")
check("teapot" in labels, f"label still reported when nothing found (got {labels})")

# --- 4. point form ------------------------------------------------------------
inst, labels = parse_response("handle<box><500><250></box>", W, H)
check(len(inst) == 1 and inst[0]["point"] is not None,
      "two-coordinate block parses as a point")
if inst and inst[0]["point"]:
    px, py = inst[0]["point"]
    check(abs(px - 500.0) < 1e-6 and abs(py - 125.0) < 1e-6,
          f"point is (x, y) = (500, 125) px (got {px:.1f},{py:.1f})")

# --- 5. multi-category query --------------------------------------------------
two = "bottle<box><0><100><0><100></box>basket<box><400><600><400><600></box>"
inst, labels = parse_response(two, W, H)
check([i["label"] for i in inst] == ["bottle", "basket"],
      f"labels track their own boxes (got {[i['label'] for i in inst]})")

# --- 6. live round-trip (opt-in) ----------------------------------------------
ap = argparse.ArgumentParser()
ap.add_argument("--endpoint", default=None, help="e.g. http://127.0.0.1:8115")
ap.add_argument("--image", default=None)
ap.add_argument("--query", default="bottle</c>basket")
ap.add_argument("--world", default=None, help="optional world_*.npy to index")
args, _ = ap.parse_known_args()

if args.endpoint and args.image:
    import numpy as np

    from rpent.utils.http_rpc import HttpRpcClient
    from rpent.utils.locateanything_client import LocateAnythingClient

    client = LocateAnythingClient(HttpRpcClient(args.endpoint))
    result = client.locate(args.image, query=args.query)
    print(f"\nlive: found={result.found} n={result.n_instances} labels={result.labels}")
    for i in result.instances:
        print(f"  {i.label:24s} center_rc={[round(v, 1) for v in i.center_rc]}")

    check(result.found, "live query found at least one instance")
    if result.image_size:
        w, h = result.image_size
        for i in result.instances:
            r, c = i.center_rc
            check(0 <= r < h and 0 <= c < w,
                  f"{i.label!r} centre inside image ({r:.0f},{c:.0f}) vs {h}x{w}")
    if args.world and result.instances:
        world = np.load(args.world)
        for i in result.instances:
            r, c = i.center_row_col_int
            if 0 <= r < world.shape[0] and 0 <= c < world.shape[1]:
                xyz = world[r, c]
                print(f"  {i.label:24s} world_xyz={[round(float(v), 3) for v in xyz]}")
                check(np.isfinite(xyz).all(), f"{i.label!r} world point is finite")
else:
    print("\nskip live round-trip (pass --endpoint and --image to run it)")

print()
if FAILURES:
    print(f"{len(FAILURES)} check(s) failed")
    raise SystemExit(1)
print("OK -- coordinate convention, instance multiplicity, none-handling, point form")
