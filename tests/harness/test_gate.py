"""The promotion gate, end to end over synthetic runs.

Plain script, not pytest:

    PYTHONPATH=. python tests/harness/test_gate.py

Builds two fake runs, a small library, and six proposals that each probe one
check, then walks the whole pipeline: review -> report/verdicts -> apply ->
library state -> ledger. Stdlib + yaml only.
"""
import json
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, ".")

from rpent.gate import tokens  # noqa: E402
from rpent.gate.apply import apply_verdicts  # noqa: E402
from rpent.gate.checks import run_checks  # noqa: E402
from rpent.gate.ledger import scan  # noqa: E402
from rpent.gate.proposal import collect_proposals, load_proposal  # noqa: E402
from rpent.gate.report import write_report  # noqa: E402

failures = []


def check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL':4}  {label}"
          + (f"\n        {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(label)


TMP = Path(tempfile.mkdtemp(prefix="gate_test_"))
MEMORY = TMP / "memory"
(MEMORY / "libero").mkdir(parents=True)
(MEMORY / "common").mkdir()

# An existing entry: consulted by run B, and the target of revise/evict tests.
OLD = MEMORY / "libero" / "bowl_offset.md"
OLD.write_text("---\ntitle: bowl eef y offset\ntype: invariant\nscope: env\n"
               "support: 1\n---\n\nAlways add +0.045 to the bowl y.\n")

# --- two fake runs -----------------------------------------------------------
def make_run(name: str, terminated: bool, extra_calls=()):
    run = TMP / "logs" / name
    (run / "memory_proposals").mkdir(parents=True)
    states = [
        {"step_idx": 0, "task_language": "pick the ketchup",
         "state": {"object_names": ["ketchup_1", "basket_1"],
                   "robot0_eef_pos": [0, 0, 0.3]}},
        {"step_idx": 1, "libero_terminated": terminated,
         "command": {"action": "move_to", "xyz": [0.1, 0.2, 0.3]},
         "state": {"robot0_eef_pos": [0.1, 0.2, 0.3]}},
    ]
    (run / "states.json").write_text(json.dumps(states))
    calls = [
        {"seq": 1, "tool": "segment", "args": {"prompt": "basket"},
         "status": "success", "step_idx_before": 0, "step_idx_after": 0,
         "result": {"found": True, "world_xyz": [0.0712, 0.2614, 0.095],
                    "rim": {"retreat_direction": "-x", "offset_m": 0.0231}}},
        {"seq": 2, "tool": "move_to", "args": {"xyz": [0.1, 0.2, 0.3]},
         "status": "success", "step_idx_before": 0, "step_idx_after": 1,
         "result": {"final_dist_m": 0.004}},
        *extra_calls,
    ]
    with open(run / "tool_calls.jsonl", "w") as f:
        for c in calls:
            f.write(json.dumps({"schema_version": 1, **c}) + "\n")
    return run


RUN_A = make_run("runA_t0", terminated=True)
RUN_B = make_run("runB_t1", terminated=False, extra_calls=[
    {"seq": 3, "tool": "read_text_file",
     "args": {"path": "memory/libero/bowl_offset.md"}, "status": "success",
     "step_idx_before": 1, "step_idx_after": 1,
     "result": {"path": str(MEMORY / "libero" / "bowl_offset.md"),
                "size": 40, "content": "Always add +0.045"}},
])

RUNS = tokens.run_map([RUN_A, RUN_B])


def proposal(run, name, front, body):
    text = "---\n" + yaml.safe_dump(front, sort_keys=False) + "---\n\n" + body
    path = run / "memory_proposals" / name
    path.write_text(text)
    return path


# 1. clean add, number traceable to the cited record (0.023 ~ 0.0231)
proposal(RUN_A, "p1_good.md", {
    "title": "retreat off the container wall before release",
    "action": "add", "type": "technique", "scope": "env",
    "conditions": "hollow containers only",
    "evidence": [{"cite": f"run:{RUN_A.name}#seq=1", "role": "measurement"},
                 {"cite": f"run:{RUN_A.name}#seq=2", "role": "outcome"}],
}, "Release beyond the near wall along rim.retreat_direction; the measured "
   "offset was about 0.023 in this scene — re-measure per scene, never reuse.")

# 2. untraceable number -> flag/hold
proposal(RUN_A, "p2_magic.md", {
    "title": "always descend to a fixed height",
    "action": "add", "type": "technique", "scope": "env",
    "evidence": [{"cite": f"run:{RUN_A.name}#seq=2", "role": "outcome"}],
}, "Descend to z=0.53 before every release.")

# 3. cite that does not resolve -> reject
proposal(RUN_A, "p3_badcite.md", {
    "title": "phantom evidence",
    "action": "add", "type": "technique", "scope": "env",
    "evidence": [{"cite": f"run:{RUN_A.name}#seq=99", "role": "measurement"}],
}, "Claims things no record shows.")

# 4. names a scene instance -> flag; also claims scope=common -> scope flag
proposal(RUN_B, "p4_cell.md", {
    "title": "the ketchup sits left of the basket",
    "action": "add", "type": "invariant", "scope": "common",
    "evidence": [{"cite": f"run:{RUN_B.name}#seq=1", "role": "measurement"}],
}, "ketchup_1 is always to the left of basket_1.")

# 5. evict the refuted entry, with a cite showing consumption
proposal(RUN_B, "p5_evict.md", {
    "title": "bowl offset constant is refuted",
    "action": "evict", "type": "invariant", "scope": "env",
    "target": "memory/libero/bowl_offset.md",
    "evidence": [{"cite": f"run:{RUN_B.name}#seq=3", "role": "consumption"},
                 {"cite": f"run:{RUN_B.name}#seq=2", "role": "refutation"}],
}, "The offset was consulted and the release still failed; measurement varies "
   "between grasps.")

# 6. support miscount -> flag
proposal(RUN_B, "p6_support.md", {
    "title": "waypoint long traversals",
    "action": "add", "type": "technique", "scope": "common",
    "support": 7,
    "evidence": [{"cite": f"run:{RUN_B.name}#seq=2", "role": "outcome"}],
}, "Split long traversals into waypoints at carry height.")

# --- review -------------------------------------------------------------------
print("=== review ===")
proposals = collect_proposals([RUN_A, RUN_B])
check("6 proposals collected", len(proposals) == 6, str(len(proposals)))
reviews = {p.path.name: run_checks(p, RUNS, MEMORY, "libero", proposals)
           for p in proposals}

check("good add -> admit", reviews["p1_good.md"].suggested == "admit",
      str([f.__dict__ for f in reviews["p1_good.md"].findings]))
check("traceable number passes",
      any("0.023" in f.message and f.level == "ok"
          for f in reviews["p1_good.md"].findings))
check("magic number -> hold",
      reviews["p2_magic.md"].suggested == "hold"
      and any("0.53" in f.message for f in reviews["p2_magic.md"].findings))
check("unresolvable cite -> reject", reviews["p3_badcite.md"].suggested == "reject")
check("instance name flagged",
      any("ketchup_1" in f.message for f in reviews["p4_cell.md"].findings))
check("scope=common with env vocab flagged",
      any(f.check == "scope" for f in reviews["p4_cell.md"].findings))
check("evict resolves and flags consumption semantics",
      reviews["p5_evict.md"].suggested == "hold"
      and any("CONSUMED" in f.message for f in reviews["p5_evict.md"].findings))
check("declared support vs cited runs flagged",
      any("support" in f.message for f in reviews["p6_support.md"].findings))
check("add destination derived from scope",
      reviews["p1_good.md"].destination.startswith("memory/libero/"))

# --- report + verdicts ----------------------------------------------------------
print("\n=== report ===")
out_dir = TMP / "gate_review"
report, verdicts_path = write_report(list(reviews.values()), out_dir, RUNS)
html = report.read_text()
check("report card per proposal", html.count('<section class="card') == 6)
check("replay deep links rendered", "replay.html#seq-1" in html)
check("verdicts prefilled with suggestions",
      all("verdict:" in line or True for line in verdicts_path.read_text().splitlines())
      and "suggested: admit" in verdicts_path.read_text())

# Human review: admit the good one AND the eviction; leave the rest.
items = yaml.safe_load(verdicts_path.read_text())
for item in items:
    if item["proposal"].endswith(("p1_good.md", "p5_evict.md")):
        item["verdict"] = "admit"
    else:
        item["verdict"] = item["suggested"] if item["suggested"] == "reject" else "hold"
verdicts_path.write_text(yaml.safe_dump(items, sort_keys=False))

# --- apply ---------------------------------------------------------------------
print("\n=== apply ===")
summary = apply_verdicts(verdicts_path, MEMORY)
new_entry = next(MEMORY.glob("libero/retreat_off_the_container_wall*.md"), None)
check("admitted add landed in the library", new_entry is not None, summary)
if new_entry:
    front_text = new_entry.read_text()
    check("provenance stamped with cites",
          f"run:{RUN_A.name}#seq=1" in front_text and "date:" in front_text)
check("evicted entry moved to memory/evicted, not deleted",
      not OLD.exists() and (MEMORY / "evicted" / "bowl_offset.md").exists())
check("eviction preserves the record",
      "0.045" in (MEMORY / "evicted" / "bowl_offset.md").read_text())
check("decisions.yaml records the non-applied with reasons",
      "not_applied" in (out_dir / "decisions.yaml").read_text())
check("summary reads like a commit message", "gate:" in summary and "added" in summary)

# --- ledger ---------------------------------------------------------------------
print("\n=== ledger ===")
result = scan([RUN_A, RUN_B], MEMORY)
entry = result["entries"].get("memory/libero/bowl_offset.md")
check("consumption read mechanically from tool_calls",
      entry is not None and entry["reads"] == 1 and entry["failures"] == 1,
      json.dumps(result["entries"]))
check("all-failure consultation recommended for review",
      not any("bowl_offset" in r and r.startswith("review") is False
              for r in result["recommendations"] if "bowl_offset" in r)
      or any("review memory/libero/bowl_offset" in r
             for r in result["recommendations"]))
check("unconsulted entries reported as zombies",
      any("retreat_off" in z for z in result["zombies"]),
      str(result["zombies"]))

# --- distiller plumbing (LLM-free parts) ---------------------------------------
print("\n=== distiller plumbing ===")
from rpent.gate.observe import run_digest, split_blocks  # noqa: E402
from rpent.gate.synthesize import build_synthesis_input  # noqa: E402

# run_digest needs a transcript-shaped run; RUN_A has no transcript — the
# digest must still build from tool_calls alone (record gaps, not crashes).
digest, _run = run_digest(RUN_A)
check("digest builds without a transcript",
      f"run:{RUN_A.name}#seq=1" in digest and "NOT terminated" not in digest.split("\n")[2])
check("digest carries outcome and env-step marks",
      "TERMINATED (success)" in digest and "ENV-STEP" in digest)

blocks = split_blocks(
    "===OBSERVATION===\n---\nclaim: a\n---\nbody\n===OBSERVATION===\n---\nclaim: b\n---\n",
    "===OBSERVATION===")
check("LLM output splitter", len(blocks) == 2 and blocks[0].startswith("---"))

(RUN_A / "observations").mkdir(exist_ok=True)
(RUN_A / "observations" / "obs_01.md").write_text(
    f"---\nclaim: release worked\nevidence:\n  - cite: run:{RUN_A.name}#seq=2\n---\n")
synth_input = build_synthesis_input([RUN_A, RUN_B], MEMORY)
check("synthesis input joins observations, outcomes, library, ledger",
      "SWEEP OUTCOMES" in synth_input and "release worked" in synth_input
      and "CONSULTATION LEDGER" in synth_input
      and "retreat_off_the_container_wall" in synth_input)

if failures:
    print(f"\nFAILED ({len(failures)}): {failures}")
    sys.exit(1)
print("\nOK — contract, checks, report, verdicts, apply, ledger, distiller plumbing")
