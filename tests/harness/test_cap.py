"""Code-as-policy in-loop half: namespace safety and the program executor.

Plain script, not pytest:

    PYTHONPATH=. python tests/harness/test_cap.py

Runs anywhere: the API binding to the real tool layer is exercised on the
box (needs the tool imports); here the executor runs against a stubbed API,
which is exactly the seam the design promises (the program only ever sees
callables).
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")

from rpent.cap import api as cap_api  # noqa: E402
from rpent.dashboard.events import NullDashboardEventSink  # noqa: E402

failures = []


def check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL':4}  {label}"
          + (f"\n        {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(label)


# --- namespace safety --------------------------------------------------------
print("=== exec namespace ===")
calls = []
stub_api = {
    "segment": lambda **kw: calls.append(("segment", kw)) or {"found": True,
                                                              "world_xyz": [0.1, 0.2, 0.3]},
    "move_to": lambda **kw: calls.append(("move_to", kw)) or {"final_dist_m": 0.003},
}


def _finish(status, summary):
    raise cap_api.ProgramHalt(status, summary)


stub_api["finish"] = _finish
ns = cap_api.exec_namespace(stub_api)

check("__import__ is the whitelist shim, not the real one",
      ns["__builtins__"]["__import__"] is cap_api._safe_import)
check("no open/eval/exec", all(k not in ns["__builtins__"]
                               for k in ("open", "eval", "exec", "compile")))
check("math/json provided", ns["math"].pi > 3 and ns["json"] is json)

try:
    exec("import os", dict(ns))
    check("import os blocked", False)
except ImportError:
    check("import os blocked", True)
ns2 = dict(ns)
exec("import math\nx = math.sqrt(9)", ns2)
check("import math tolerated (smoke-run lesson: a no-op import must not "
      "kill an episode)", ns2["x"] == 3.0)

# --- instrumentation: program calls must land in tool_calls.jsonl -----------
print("\n=== instrumentation ===")
import tempfile as _tf  # noqa: E402

from rpent.tools import tool_log  # noqa: E402

LOGDIR = Path(_tf.mkdtemp(prefix="cap_log_"))


class Ctx:
    step_idx = 0


ctx = Ctx()


def fake_move(**kw):
    ctx.step_idx += 1
    return {"final_dist_m": 0.004}


def fake_bad(**kw):
    raise RuntimeError("boom")


tool_log.reset_sequence()
inst_move = cap_api.instrument("move_to", fake_move, ctx, LOGDIR)
inst_bad = cap_api.instrument("segment", fake_bad, ctx, LOGDIR)
inst_move(xyz=[1, 2, 3])
try:
    inst_bad(prompt="x")
except RuntimeError:
    pass
records = tool_log.load(LOGDIR)
check("both calls recorded (smoke-run lesson: program runs logged ZERO calls)",
      [r["tool"] for r in records] == ["move_to", "segment"], str(records))
check("step advance visible in the record",
      records[0]["step_idx_before"] == 0 and records[0]["step_idx_after"] == 1)
check("raised call recorded with status=raised",
      records[1]["status"] == "raised" and "boom" in json.dumps(records[1]))

# --- ProgramPlanner ----------------------------------------------------------
print("\n=== ProgramPlanner ===")
from rpent.planner import program as program_mod  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="cap_test_"))
PROGRAM = TMP / "solve.py"
PROGRAM.write_text(
    "r = segment(prompt='bowl', entity='bowl')\n"
    "if r['found']:\n"
    "    move_to(xyz=r['world_xyz'], gripper=-1.0)\n"
    "    finish('success', 'moved to the bowl')\n"
    "finish('stuck', 'no bowl')\n"
)


class StubToolkit:
    tool_context = object()


# The planner asks cap.api for the binding; stub it so no tool imports run here.
cap_api.make_api = lambda ctx, output_dir=None: dict(stub_api)

out_dir = TMP / "run"
out_dir.mkdir()
planner = program_mod.ProgramPlanner(program_file=str(PROGRAM), output_dir=out_dir,
                                     dashboard_events=NullDashboardEventSink())
result = planner.solve(system_prompt="", user_message="", toolkit=StubToolkit(),
                       max_turns=1)
check("finish captured via ProgramHalt",
      result.finish_result == {"_finish": True, "status": "success",
                               "summary": "moved to the bowl"},
      str(result.finish_result))
check("api calls executed in order",
      [c[0] for c in calls] == ["segment", "move_to"], str(calls))
check("program + hash recorded as run evidence",
      (out_dir / "program.py").exists()
      and len(json.loads((out_dir / "program.json").read_text())["sha256"]) == 64)
check("no error on clean halt", result.error is None, str(result.error))

# A raising program leaves a crime scene, not a crash.
BAD = TMP / "bad.py"
BAD.write_text("x = 1/0\n")
planner_bad = program_mod.ProgramPlanner(program_file=str(BAD), output_dir=out_dir,
                                         dashboard_events=NullDashboardEventSink())
result_bad = planner_bad.solve(system_prompt="", user_message="",
                               toolkit=StubToolkit(), max_turns=1)
check("traceback saved to analysis/program_error.txt",
      "ZeroDivisionError" in (out_dir / "analysis" / "program_error.txt").read_text())
check("failure reported as finish status=error",
      result_bad.finish_result["status"] == "error"
      and "ZeroDivisionError" in result_bad.finish_result["summary"])

# --- program extraction (loop plumbing) ---------------------------------------
print("\n=== loop plumbing ===")
from rpent.cap.loop import _extract_program  # noqa: E402

reply = "thinking...\n```python\nfinish('success', 'ok')\n```\ndone"
check("program extracted from fenced block",
      _extract_program(reply) == "finish('success', 'ok')\n")
check("no block -> None", _extract_program("no code here") is None)

if failures:
    print(f"\nFAILED ({len(failures)}): {failures}")
    sys.exit(1)
print("\nOK — namespace safety, executor, evidence, extraction")
