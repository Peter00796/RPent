"""The run sandbox: profiles, enforcement, write protection, fail-closed.

Plain script, not pytest, like the other harness tests:

    PYTHONPATH=. python tests/harness/test_sandbox.py

Stdlib + PyYAML only — no langchain, no GPU — so it runs anywhere.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")

from rpent.tools import common, sandbox  # noqa: E402
from rpent.utils.config import get_repo_root  # noqa: E402

failures = []


def check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL':4}  {label}"
          + (f"\n        {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(label)


TMP = Path(tempfile.mkdtemp(prefix="sandbox_test_"))
OUT = TMP / "run_out"
OUT.mkdir()
SECRET = TMP / "outside" / "env_calibration.md"
SECRET.parent.mkdir()
SECRET.write_text("z=0.53")

BINDINGS = {
    "output_dir": str(OUT),
    "repo_root": str(TMP),
    "memory_common": str(TMP / "memory" / "common"),
    "memory_env": str(TMP / "memory" / "libero"),
    "staging_root": str(TMP / ".staging" / "libero"),
}

# --- A. shipped profiles load and resolve --------------------------------
print("=== A. shipped profiles ===")
for name, n_read, uses_staging in (
    ("none", 1, False), ("memory", 3, False), ("full", 4, True),
    ("unrestricted", 1, False),
):
    pol = sandbox.load_profile(name, BINDINGS)
    check(f"{name}: loads, {n_read} read roots",
          len(pol.read_roots) == n_read and pol.name == name,
          str(pol.read_roots))
    check(f"{name}: write root is output_dir only",
          pol.write_roots == (OUT.resolve(),), str(pol.write_roots))
    check(f"{name}: uses_staging={uses_staging}",
          pol.uses_staging is uses_staging)

try:
    sandbox.load_profile("nonexistent", BINDINGS)
    check("unknown profile rejected", False)
except FileNotFoundError as e:
    check("unknown profile rejected, lists available",
          "memory" in str(e) and "none" in str(e), str(e))

bad = TMP / "bad.yaml"
bad.write_text("name: bad\nread_roots: ['{nope}']\nwrite_roots: ['{output_dir}']\n")
try:
    sandbox.load_profile(str(bad), BINDINGS)
    check("unknown placeholder rejected", False)
except ValueError as e:
    check("unknown placeholder rejected with known list",
          "nope" in str(e) and "output_dir" in str(e), str(e))

bad2 = TMP / "bad2.yaml"
bad2.write_text("name: bad2\nread_roots: ['{output_dir}']\n"
                "write_roots: ['{output_dir}']\nextra_key: 1\n")
try:
    sandbox.load_profile(str(bad2), BINDINGS)
    check("unknown profile key rejected", False)
except ValueError as e:
    check("unknown profile key rejected", "extra_key" in str(e), str(e))

# --- B. fail-closed before initialisation --------------------------------
print("\n=== B. fail-closed ===")
sandbox.clear_sandbox()
r = common.read_text_file(str(SECRET))
check("uninitialised sandbox denies reads",
      "error" in r and "not initialised" in r["error"], str(r))
w = common.write_text_file(str(TMP / "x.txt"), "hi")
check("uninitialised sandbox denies writes",
      "error" in w and "not initialised" in w["error"], str(w))

# --- C. enforcement under the 'none' profile ------------------------------
print("\n=== C. enforcement (none profile) ===")
sandbox.set_sandbox(sandbox.load_profile("none", BINDINGS))

inside = OUT / "notes.txt"
w = common.write_text_file(str(inside), "measured, not recalled")
check("write inside output_dir allowed", w.get("bytes_written") == 22, str(w))
r = common.read_text_file(str(inside))
check("read inside output_dir allowed",
      r.get("content") == "measured, not recalled", str(r))

r = common.read_text_file(str(SECRET))
check("read outside denied with allowed_roots",
      "error" in r and r.get("allowed_roots") == [str(OUT.resolve())], str(r))
check("denial does not leak the file's content", "z=0.53" not in json.dumps(r))

w = common.write_text_file(str(TMP / "escape.txt"), "nope")
check("write outside denied", "error" in w and "allowed_roots" in w, str(w))
check("denied write did not happen", not (TMP / "escape.txt").exists())

d = common.list_dir(str(SECRET.parent))
check("list_dir outside denied", "error" in d and "allowed_roots" in d, str(d))
d = common.list_dir(str(OUT))
check("list_dir inside allowed", d.get("count", -1) >= 1, str(d))

# relative paths resolve against the repo root -> outside the sandbox
r = common.read_text_file("robots/libero/guides/env_calibration.md")
check("repo-relative prior path denied", "error" in r, str(r))

# symlink escape: a link inside the sandbox pointing outside
link = OUT / "innocent.md"
os.symlink(SECRET, link)
r = common.read_text_file(str(link))
check("symlink escape denied (checked post-resolve)", "error" in r, str(r))

# --- D. memory profile exposes the library read-only ----------------------
print("\n=== D. memory profile ===")
mem = Path(BINDINGS["memory_env"])
mem.mkdir(parents=True)
(mem / "gripper_axis.md").write_text("fingers close along eef y")
sandbox.set_sandbox(sandbox.load_profile("memory", BINDINGS))
r = common.read_text_file(str(mem / "gripper_axis.md"))
check("memory readable", r.get("content") == "fingers close along eef y", str(r))
w = common.write_text_file(str(mem / "sneaky.md"), "self-promoted")
check("memory NOT writable (gate-only)", "error" in w, str(w))
check("proposal path inside output_dir writable",
      "error" not in common.write_text_file(
          str(OUT / "memory_proposals" / "p1.md"), "claim + evidence"))

# --- E. write protection over harness artifacts ---------------------------
print("\n=== E. write protection ===")
(OUT / "states.json").write_text("[]")  # harness writes it, not the agent
sandbox.add_write_protection([OUT / "states.json", OUT / "tool_calls.jsonl",
                              OUT / "world"])
w = common.write_text_file(str(OUT / "states.json"), "[]")
check("states.json is agent-read-only", "error" in w and "harness-owned" in w["error"], str(w))
w = common.write_text_file(str(OUT / "world" / "world_00.npy"), "x")
check("protected dir contents agent-read-only", "error" in w, str(w))
r = common.read_text_file(str(OUT / "states.json"))
check("protected artifact still readable", r.get("content") == "[]", str(r))
w = common.write_text_file(str(OUT / "audit.json"), "{}")
check("agent outputs (audit/recipe) still writable", "error" not in w, str(w))

# --- F. fingerprint --------------------------------------------------------
print("\n=== F. fingerprint ===")
pol = sandbox.init_run_sandbox("none", "libero", OUT)
fp = json.loads((OUT / "sandbox.json").read_text())
check("sandbox.json written with profile + hash + resolved roots",
      fp["profile"] == "none" and len(fp["source_sha256"]) == 64
      and fp["read_roots"] == [str(OUT.resolve())], json.dumps(fp))
pol2 = sandbox.load_profile("none", BINDINGS)
check("same profile file -> same hash (fingerprint is stable)",
      pol.source_sha256 == pol2.source_sha256)
# repo bindings differ from test bindings -> resolved roots differ, hash same
repo_pol = sandbox.load_profile(
    "none", sandbox.default_bindings("libero", OUT))
check("default_bindings resolves under the repo root",
      str(get_repo_root()) in json.dumps(
          sandbox.default_bindings("libero", OUT)))

# Practice profile: the task-playbook root binds only when the runner
# supplies suite/task; without them the profile fails loudly, not silently.
task_bindings = dict(BINDINGS)
task_bindings["memory_task"] = str(TMP / "memory" / "tasks" / "suite_x" / "t5")
practice = sandbox.load_profile("practice", task_bindings)
check("practice profile exposes the task playbook root",
      len(practice.read_roots) == 4
      and any(str(p).endswith("t5") for p in practice.read_roots))
try:
    sandbox.load_profile("practice", BINDINGS)
    check("practice without suite/task binding fails loudly", False)
except ValueError as e:
    check("practice without suite/task binding fails loudly",
          "memory_task" in str(e), str(e))
check("default_bindings adds memory_task only with suite+task",
      "memory_task" not in sandbox.default_bindings("libero", OUT)
      and sandbox.default_bindings("libero", OUT,
          {"suite": "s", "task": 5})["memory_task"].endswith("tasks/s/t5"))

# The recorded fingerprint must track write protection registered later
# (the toolkit registers it AFTER init_run_sandbox's first dump).
sandbox.add_write_protection([OUT / "states.json"])
fp2 = json.loads((OUT / "sandbox.json").read_text())
check("fingerprint re-dumped when write protection registers",
      any(p.endswith("states.json") for p in fp2["write_denied"]),
      json.dumps(fp2["write_denied"]))

sandbox.clear_sandbox()
if failures:
    print(f"\nFAILED ({len(failures)}): {failures}")
    sys.exit(1)
print("\nOK — sandbox profiles, enforcement, write protection, fingerprint")
