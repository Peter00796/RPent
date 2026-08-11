"""The practice loop, dry-run with fakes — no GPU, no API.

Plain script:  PYTHONPATH=. python tests/harness/test_practice.py

Covers the three arcs: failure mined into an auto-admitted playbook entry;
knowledge stall escalating to the miner's own open question; practice
passing triggering the exam and the exam verdict ending the loop.
"""
import json
import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, ".")

failures = []


def check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL':4}  {label}"
          + (f"\n        {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(label)


TMP = Path(tempfile.mkdtemp(prefix="practice_test_"))
LOGS = TMP / "logs"; LOGS.mkdir()
REPO_MEM = TMP / "memory"; (REPO_MEM / "tasks").mkdir(parents=True)

# Repo root override so playbooks land in the temp tree.
import os  # noqa: E402

os.environ["RPENT_REPO_ROOT"] = str(TMP)

# Fake chat BEFORE importing the loop (it imports lazily inside functions).
SCRIPT = {"round": 0}
PROPOSAL_OK = """===PROPOSAL===
---
title: use the shape phrasing for the slab
action: add
type: technique
scope: task
task: fake_suite/t9
conditions: grasp phase
evidence:
  - cite: run:{run}#seq=1
    role: name prompt failed
  - cite: run:{run}#seq=2
    role: shape prompt held
counter_evidence: []
---
Use the shape-descriptive phrasing; verify the hold geometrically.
"""
STALLED = """no proposals this time
===OPEN QUESTION===
Which descend depth holds the slab: top-0.005 or top+0.005?
"""


class FakeChat:
    def invoke(self, messages):
        # round 1: a clean proposal; round 2 (if asked): stall + question
        text = (PROPOSAL_OK.format(run=SCRIPT["last_failed"])
                if SCRIPT["round"] == 1 else STALLED)
        return types.SimpleNamespace(content=text)


sys.modules["langchain.chat_models"] = types.SimpleNamespace(
    init_chat_model=lambda m, **k: FakeChat())

from rpent.practice import loop as L  # noqa: E402

# Fake episodes: script per (seed, round) outcomes.
PLAN = {}  # (tag) -> terminated?
COUNTER = {"n": 0}


def fake_sh(cli_args, log_path, timeout_s=1500):
    return 0


def make_run(seed: int, terminated: bool) -> Path:
    COUNTER["n"] += 1
    d = LOGS / f"20990101-{COUNTER['n']:02d}_fake_suite_t9_s{seed}"
    d.mkdir()
    (d / "states.json").write_text(json.dumps(
        [{"step_idx": 0}, {"step_idx": 1, "libero_terminated": terminated}]))
    with open(d / "tool_calls.jsonl", "w") as f:
        f.write(json.dumps({"seq": 1, "tool": "pi0_pick",
                            "args": {"prompt": "name"}, "status": "success",
                            "step_idx_before": 0, "step_idx_after": 0,
                            "result": {"ok": False}}) + "\n")
        f.write(json.dumps({"seq": 2, "tool": "pi0_pick",
                            "args": {"prompt": "shape"}, "status": "success",
                            "step_idx_before": 0, "step_idx_after": 1,
                            "result": {"ok": True}}) + "\n")
    SCRIPT["last_failed"] = d.name
    return d


EPISODES = []  # queue of terminated flags, consumed in order


def fake_episode_runner(logs_root, suite, task, seed):
    return make_run(seed, EPISODES.pop(0))


L._sh = fake_sh
L._newest_run = lambda logs_root, suite, task, seed: fake_episode_runner(
    logs_root, suite, task, seed)
L.observe_run = lambda run, model, base_url: (
    (run / "observations").mkdir(exist_ok=True),
    (run / "observations" / "obs_01.md").write_text(
        f"---\nclaim: shape worked, name failed\nevidence:\n"
        f"  - cite: run:{run.name}#seq=2\n---\n"),
)[0]

# Arc: round1 practice fails (2 seeds) -> proposal admitted; round2 practice
# passes both -> exam passes -> solved.
EPISODES[:] = [False, False,   # round 1 practice
               True, True,     # round 2 practice
               True]           # round 2 exam
SCRIPT["round"] = 1
result = L.practice_loop(suite="fake_suite", task=9, practice_seeds=[51, 52],
                         exam_seed=0, max_rounds=3, model="fake",
                         base_url=None, logs_root=LOGS)
print("=== arc 1: fail -> learn -> pass -> exam ===")
check("loop reports solved", result["solved"] is True, json.dumps(result))
check("exam counted", result["exams_taken"] == 1)
entry = (REPO_MEM / "tasks" / "fake_suite" / "t9")
check("playbook entry auto-admitted",
      entry.is_dir() and any(entry.glob("use_the_shape*.md")),
      str(list(entry.glob("*"))))
check("history written", (LOGS / "practice_fake_suite_t9" / "history.json").exists())
check("round review recorded",
      any((LOGS / "practice_fake_suite_t9" / "round_01").glob("review_*.json")))

# Arc 2: stall -> open question -> experiment episode next round.
SCRIPT["round"] = 2
EPISODES[:] = [False, False,   # round 1 practice fails
               False,          # round 2 = experiment episode (one seed)
               ]
result2 = L.practice_loop(suite="fake_suite", task=9, practice_seeds=[51, 52],
                          exam_seed=0, max_rounds=2, model="fake",
                          base_url=None, logs_root=LOGS)
print("\n=== arc 2: stall -> experiment escalation ===")
hist = result2["history"]
check("no admission on stall", hist[0].get("admitted") == [])
check("open question queued",
      str(hist[0].get("next", "")).startswith("experiment: Which descend"),
      json.dumps(hist))
check("round 2 ran the experiment", "experiment" in hist[1], json.dumps(hist[1]))

if failures:
    print(f"\nFAILED ({len(failures)}): {failures}")
    sys.exit(1)
print("\nOK — mine/admit, stall/escalate, exam arcs")
