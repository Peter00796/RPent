"""Audit every model-facing description against the pre-refactor original.

Compares the descriptions the planner now sees (docstrings + Field descriptions,
rendered through the native LangChain tools) against TOOLS_SPEC at git HEAD.
Whitespace is normalised because docstrings reflow; any other difference is real.
"""
import ast
import re
import subprocess
import sys
from pathlib import Path

REPO = Path("/Users/yanxinpeng/Desktop/Spring2026/PRAxIs/RPent")
sys.path.insert(0, str(REPO))

from rpent.utils.logging import init_output_dir  # noqa: E402

init_output_dir(Path(__file__).parent / "audit_out")
from robots.libero.tools.legacy_specs import legacy_tool_specs  # noqa: E402


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


old_src = subprocess.run(
    ["git", "-C", str(REPO), "show", "HEAD:robots/libero/tools.py"],
    capture_output=True, text=True, check=True,
).stdout
tree = ast.parse(old_src)
old = None
for node in tree.body:
    if isinstance(node, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id == "TOOLS_SPEC" for t in node.targets
    ):
        old = ast.literal_eval(node.value)
assert old is not None
OLD = {s["name"]: s for s in old}
NEW = {s["name"]: s for s in legacy_tool_specs()}

print(f"tools: HEAD={len(OLD)}  now={len(NEW)}")
missing = sorted(set(OLD) - set(NEW))
extra = sorted(set(NEW) - set(OLD))
if missing:
    print("  !! MISSING TOOLS:", missing)
if extra:
    print("  !! EXTRA TOOLS:", extra)

problems = []

for name in OLD:
    if name not in NEW:
        continue
    o, n = OLD[name], NEW[name]

    # --- tool description ---
    od, nd = norm(o["description"]), norm(n["description"])
    if od != nd:
        problems.append(("TOOL DESC", name, od, nd))

    # --- parameter sets ---
    op = o["input_schema"].get("properties", {})
    np_ = n["input_schema"].get("properties", {})
    lost = sorted(set(op) - set(np_))
    added = sorted(set(np_) - set(op))
    if lost:
        problems.append(("PARAM LOST", name, ", ".join(lost), ""))
    if added:
        problems.append(("PARAM ADDED", name, "", ", ".join(added)))

    # --- required sets ---
    oreq = set(o["input_schema"].get("required", []))
    nreq = set(n["input_schema"].get("required", []))
    if oreq != nreq:
        problems.append(("REQUIRED", name, str(sorted(oreq)), str(sorted(nreq))))

    # --- per-parameter descriptions ---
    for p in sorted(set(op) & set(np_)):
        od2 = norm(op[p].get("description"))
        nd2 = norm(np_[p].get("description"))
        if od2 != nd2:
            problems.append((f"PARAM DESC {p}", name, od2, nd2))
        # enum preservation
        oe, ne = op[p].get("enum"), np_[p].get("enum")
        if oe and oe != ne:
            problems.append((f"ENUM {p}", name, str(oe), str(ne)))

print()
if not problems:
    print("✅ every tool description and every parameter description matches HEAD")
else:
    print(f"⚠ {len(problems)} difference(s):\n")
    for kind, name, o, n in problems:
        print(f"── {name}  [{kind}]")
        print(f"   HEAD: {o[:220]}")
        print(f"   NOW : {n[:220]}")
        print()
