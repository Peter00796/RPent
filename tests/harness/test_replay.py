"""Evidence replay over a synthetic run with known geometry.

Plain script, not pytest:

    PYTHONPATH=. python tests/harness/test_replay.py

Builds a tiny run directory from scratch (world maps with known coordinates,
hand-encoded PNGs, a three-call transcript) and checks that the timeline
loads, the projection is exact, and the HTML carries the anchors and markers
the promotion gate will deep-link. Stdlib + numpy only.
"""
import json
import struct
import sys
import tempfile
import zlib
from pathlib import Path

import numpy as np

sys.path.insert(0, ".")

from rpent.replay import html as replay_html  # noqa: E402
from rpent.replay import loader, project, render  # noqa: E402

failures = []


def check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL':4}  {label}"
          + (f"\n        {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(label)


def write_png(path: Path, width: int, height: int) -> None:
    """Minimal 8-bit RGB PNG encoder — enough for size/marker tests."""
    raw = b"".join(b"\x00" + b"\x40\x60\x80" * width for _ in range(height))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


# --- build the synthetic run ------------------------------------------------
RUN = Path(tempfile.mkdtemp(prefix="replay_test_")) / "fake_run"
(RUN / "world").mkdir(parents=True)
(RUN / "segments").mkdir()

# world map: pixel (r, c) sits at world (r/100, c/100, 0.5) — projection is
# exactly invertible, so the assert below has one right answer.
grid = np.zeros((8, 8, 3), dtype=np.float32)
for r in range(8):
    for c in range(8):
        grid[r, c] = (r / 100, c / 100, 0.5)
np.save(RUN / "world" / "world_00.npy", grid)
np.save(RUN / "world" / "world_01.npy", grid)
write_png(RUN / "images_cam" / "image_cam_00.png", 8, 8)
write_png(RUN / "images_cam" / "image_cam_01.png", 8, 8)
write_png(RUN / "segments" / "segment_overlay_00_00.png", 16, 16)

(RUN / "states.json").write_text(json.dumps([
    {"step_idx": 0, "task_language": "put the cube in the bowl",
     "state": {"robot0_eef_pos": [0.02, 0.02, 0.5]}},
    {"step_idx": 1, "state": {"robot0_eef_pos": [0.03, 0.04, 0.5]},
     "libero_terminated": False},
]))
(RUN / "sandbox.json").write_text(json.dumps({"profile": "none"}))

seg_result = {
    "found": True, "step": 0, "camera": "agentview", "score": 0.9,
    "n_pixels": 40, "world_xyz": [0.05, 0.06, 0.5],
    "box": [4.0, 2.0, 12.0, 9.0],   # [x0, y0, x1, y1] in overlay space
    "overlay_path": f"/somewhere/else/{RUN.name}/segments/segment_overlay_00_00.png",
    "looks_hollow": False,
}
calls = [
    {"seq": 1, "tool": "view_driver_state", "args": {"step": 0}, "status": "success",
     "elapsed_s": 0.01, "step_idx_before": 0, "step_idx_after": 0,
     "result": {"step": 0, "state": {"robot0_eef_pos": [0.02, 0.02, 0.5]}}},
    {"seq": 2, "tool": "segment", "args": {"prompt": "cube", "entity": "cube"},
     "status": "success", "elapsed_s": 2.0, "step_idx_before": 0,
     "step_idx_after": 0, "result": seg_result},
    {"seq": 3, "tool": "move_to", "args": {"xyz": [0.03, 0.04, 0.5], "gripper": -1.0},
     "status": "success", "elapsed_s": 5.0, "step_idx_before": 0,
     "step_idx_after": 1, "result": {"result": {"final_dist_m": 0.004}}},
]
with open(RUN / "tool_calls.jsonl", "w") as f:
    for c in calls:
        f.write(json.dumps({"schema_version": 1, **c}) + "\n")

(RUN / "transcript_fake.json").write_text(json.dumps({
    "model": "scripted", "finish": {"status": "stuck", "summary": "test"},
    "stats": {}, "messages": [
        {"role": "user", "content": "solve it"},
        {"role": "assistant", "content": [
            {"type": "text", "text": "inspect first"},
            {"type": "tool_use", "id": "c1", "name": "view_driver_state", "input": {}}]},
        {"role": "tool", "name": "view_driver_state", "tool_call_id": "c1", "content": "{}"},
        {"role": "assistant", "content": [
            {"type": "text", "text": "localize the cube, then approach it"},
            {"type": "tool_use", "id": "c2", "name": "segment", "input": {}},
            {"type": "tool_use", "id": "c3", "name": "move_to", "input": {}}]},
    ],
}))

# --- loader -------------------------------------------------------------
print("=== loader ===")
run = loader.load_run(RUN)
check("3 calls joined", len(run.calls) == 3)
check("no record gaps", run.warnings == [], str(run.warnings))
check("reasoning attached to the turn's first call",
      run.calls[1].reasoning == "localize the cube, then approach it"
      and run.calls[2].reasoning == "",
      f"{run.calls[1].reasoning!r} / {run.calls[2].reasoning!r}")
check("turns assigned", [c.turn for c in run.calls] == [1, 2, 2])
check("advancing computed from step_idx",
      [c.advanced for c in run.calls] == [False, False, True])
check("task + termination read from states",
      run.task_language == "put the cube in the bowl" and run.terminated is False)

# --- projection ----------------------------------------------------------
print("\n=== projection ===")
hit = project.world_to_pixel(RUN, 1, [0.03, 0.04, 0.5])
check("known point projects exactly", hit == (3, 4, 0.0), str(hit))
check("missing map -> None", project.world_to_pixel(RUN, 7, [0, 0, 0]) is None)
check("png_size reads IHDR", project.png_size(RUN / "images_cam" / "image_cam_00.png") == (8, 8))

# --- renderers ------------------------------------------------------------
print("\n=== renderers ===")
seg_card = render.render_call(run.calls[1], run)
check("segment overlay panel via relativized path",
      any(p.src == "segments/segment_overlay_00_00.png" for p in seg_card.panels),
      str([p.src for p in seg_card.panels]))
check("segment bbox marker is a box in [x,y] order",
      any(m.kind == "box" and m.col == 4.0 and m.row == 2.0
          for p in seg_card.panels for m in p.markers))
move_card = render.render_call(run.calls[2], run)
move_markers = [m for p in move_card.panels for m in p.markers]
check("move_to target projected onto before-image",
      any(m.kind == "target" and (m.row, m.col) == (3, 4) for m in move_markers),
      str([(m.kind, m.row, m.col) for m in move_markers]))

# --- 3d ---------------------------------------------------------------------
print("\n=== 3d ===")
from rpent.replay import three_d  # noqa: E402

html3d = three_d.build_3d_html(run)
check("3d builds from stored world maps", html3d is not None)
if html3d:
    check("3d: full call timeline embedded (markdown-rendered reasoning)",
          "localize the cube, then approach it" in html3d)
    check("3d: segment reading carries seq + entity",
          "#2 cube" in html3d, html3d[html3d.find("segment readings"):][:120])
    check("3d: deep-links to the 2D card", "replay.html#seq-" in html3d)
    check("3d: two frames (two world maps)", html3d.count('"name": "') >= 2)

# --- html ------------------------------------------------------------------
print("\n=== html ===")
out = replay_html.write_replay(run)
text = out.read_text()
check("anchors for every call", all(f'id="seq-{n}"' in text for n in (1, 2, 3)))
check("reasoning rendered", "localize the cube" in text)
check("relative img srcs only", 'src="/' not in text and "src=\"images_cam/" in text)
check("env-step badge on the advancing call only", text.count('class="adv"') == 1)
check("sandbox profile in header", "sandbox none" in text)
check("finish surfaced", "stuck" in text)

if failures:
    print(f"\nFAILED ({len(failures)}): {failures}")
    sys.exit(1)
print("\nOK — loader, projection, renderers, html")
