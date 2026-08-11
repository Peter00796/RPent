"""The inspect_image vision channel: verbatim pipe, crops, sandbox, gating.

No API calls — the reader model is a scripted fake injected via
``vision.configure(client=...)``.

    PYTHONPATH=. python tests/harness/test_vision_tool.py
"""
import base64
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
SCRATCH = Path(__file__).parent / "vision_run"
SCRATCH.mkdir(exist_ok=True)

import numpy as np  # noqa: E402
import imageio.v2 as imageio  # noqa: E402

from rpent.tools import sandbox, vision  # noqa: E402
from rpent.tools.sandbox import SandboxPolicy  # noqa: E402

failures = []


def check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL':4}  {label}"
          + (f"\n        {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(label)


class FakeReply:
    def __init__(self, content, reasoning=None):
        self.content = content
        self.additional_kwargs = (
            {"reasoning_content": reasoning} if reasoning else {})
        self.usage_metadata = {"input_tokens": 111, "output_tokens": 22}


class FakeReader:
    """Records what it was asked; replies verbatim-weird on purpose."""

    def __init__(self, reply):
        self.reply = reply
        self.seen = []

    def invoke(self, messages):
        self.seen.append(messages)
        return self.reply


# A real 64x48 image: left half red, right half blue.
img = np.zeros((48, 64, 3), dtype=np.uint8)
img[:, :32, 0] = 200
img[:, 32:, 2] = 200
IMG = SCRATCH / "scene.png"
imageio.imwrite(IMG, img)
OUTSIDE = Path("/etc/hosts")

sandbox.set_sandbox(SandboxPolicy(
    name="test-vision", source="inline", source_sha256="0", description="",
    read_roots=(SCRATCH.resolve(),), write_roots=(SCRATCH.resolve(),),
))

print("=== gating ===")
vision.clear()
r = vision.inspect_image(str(IMG), "what colour?")
check("unconfigured returns a structured error",
      "not configured" in r.get("error", ""), str(r))

WEIRD = "  well…\nCrop 2 is *maybe* redder?? 🤷 but honestly hard to say.  "
reader = FakeReader(FakeReply(WEIRD, reasoning="secret chain of thought"))
vision.configure("openai:fake-vlm", base_url="http://x", client=reader)

print("\n=== verbatim pipe ===")
r = vision.inspect_image(str(IMG), "which side is red?")
check("answer is the reply VERBATIM (whitespace, emoji, hedges intact)",
      r.get("answer") == WEIRD, repr(r.get("answer"))[:120])
check("hidden reasoning passed through unedited",
      r.get("reasoning") == "secret chain of thought", str(r.get("reasoning")))
check("sent records system line + question verbatim",
      r["sent"]["system"] == vision.SYSTEM_LINE
      and r["sent"]["question"] == "which side is red?", str(r.get("sent")))
check("vlm usage recorded", r["vlm_usage"] == {"in": 111, "out": 22},
      str(r.get("vlm_usage")))
check("model spec recorded", r["model"] == "openai:fake-vlm")
sent_user = reader.seen[-1][1]["content"]
check("no task context leaks to the reader (system is the fixed line only)",
      reader.seen[-1][0]["content"] == vision.SYSTEM_LINE)
check("full frame sent as one data-URI image block",
      sum(1 for b in sent_user if isinstance(b, dict)
          and b.get("type") == "image_url") == 1)

print("\n=== regions ===")
r2 = vision.inspect_image(str(IMG), "which crop is red?",
                          regions=[[0, 0, 48, 32], [0, 32, 48, 64]])
check("two crops -> two labeled image blocks", sum(
    1 for b in reader.seen[-1][1]["content"]
    if isinstance(b, dict) and b.get("type") == "image_url") == 2)
check("crop labels recorded verbatim in sent",
      len(r2["sent"]["crop_labels"]) == 2
      and "rows 0:48, cols 0:32" in r2["sent"]["crop_labels"][0],
      str(r2["sent"]["crop_labels"]))
# Crop 1 is the pure-red half — decode it back and verify pixels.
uri = next(b["image_url"]["url"] for b in reader.seen[-1][1]["content"]
           if isinstance(b, dict) and b.get("type") == "image_url")
crop = imageio.imread(io.BytesIO(base64.b64decode(uri.split(",", 1)[1])))
check("crop is pixel-true (left half: red channel on, blue off)",
      crop.shape[:2] == (48, 32) and crop[:, :, 0].min() == 200
      and crop[:, :, 2].max() == 0, str(crop.shape))

r3 = vision.inspect_image(str(IMG), "?", regions=[[0, 0, 999, 10]])
check("out-of-bounds region refused", "outside" in r3.get("error", ""), str(r3))
r4 = vision.inspect_image(str(IMG), "?",
                          regions=[[0, 0, 1, 1]] * 4)
check("more than 3 regions refused", "at most" in r4.get("error", ""), str(r4))

print("\n=== sandbox ===")
r5 = vision.inspect_image(str(OUTSIDE), "?")
check("path outside the sandbox refused",
      "denied" in r5.get("error", ""), str(r5))

print("\n=== surface gating ===")
from rpent.tools.langchain_common import common_tools  # noqa: E402

base_names = {t.name for t in common_tools()}
vis_names = {t.name for t in common_tools(vision=True)}
check("blind surface has no inspect_image", "inspect_image" not in base_names)
check("vision surface adds exactly inspect_image",
      vis_names - base_names == {"inspect_image"})

vision.clear()
sandbox.clear_sandbox()
print()
if failures:
    print(f"{len(failures)} CHECK(S) FAILED")
    sys.exit(1)
print("all checks passed")
