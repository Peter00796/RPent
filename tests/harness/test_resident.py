"""End-to-end check of the resident debug session (no API calls, no GPU).

Drives the real planner, real middleware (including AttemptFoldingMiddleware),
real native tools and a real LiberoContext through a scripted two-attempt
session: attempt 1 fails -> diagnose -> reset_episode -> drill into the
archive with view_attempt_call -> finish. Only the chat model, the env
primitives and begin_episode are fakes.

    PYTHONPATH=. python tests/harness/test_resident.py
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
SCRATCH = Path(__file__).parent

from rpent.utils.logging import init_output_dir  # noqa: E402

OUT = init_output_dir(SCRATCH / "resident_run")
# A stale archive or log from a previous execution would read as this run's.
for stale in OUT.glob("attempt_*"):
    shutil.rmtree(stale)
for stale in ("tool_calls.jsonl", "states.json", "analysis/entities.json",
              "resident_notes.md"):
    (OUT / stale).unlink(missing_ok=True)

from langchain_core.language_models.chat_models import BaseChatModel  # noqa: E402
from langchain_core.messages import AIMessage, ToolMessage  # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatResult  # noqa: E402

import robots.libero.tools as T  # noqa: E402
from robots.libero.tools.context import LiberoContext  # noqa: E402
from rpent.dashboard.events import NullDashboardEventSink  # noqa: E402
from rpent.planner.deep_agent import DeepAgentPlanner  # noqa: E402
from rpent.tools import sandbox, tool_log  # noqa: E402
from rpent.tools.sandbox import SandboxPolicy  # noqa: E402
from rpent.tools.toolkit import Toolkit  # noqa: E402

failures = []


def check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL':4}  {label}"
          + (f"\n        {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(label)


class ScriptedModel(BaseChatModel):
    """Replays fixed AIMessages and records what each request showed it."""

    turns: list = []
    idx: int = 0
    seen: list = []  # per _generate call: the message list it received

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kw):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(list(messages))
        msg = self.turns[min(self.idx, len(self.turns) - 1)]
        self.idx += 1
        return ChatResult(generations=[ChatGeneration(message=msg)])


class FakePrims:
    def __init__(self):
        self.saved_videos = []

    def move_to(self, **kw):
        return {"final_dist_m": 0.004}

    def pi0_pick(self, **kw):
        return {"success": False, "lift": 0.01,
                "note": "grasp closed on nothing"}

    def stop_recording_and_save(self, path, fps=20):
        Path(path).write_text("fake mp4")
        self.saved_videos.append(path)
        return {"path": path, "n_frames": 1}


class FakeToolkit(Toolkit):
    """Real LangChain surface incl. resident tools, fake primitives."""

    def __init__(self):
        super().__init__(dashboard_events=NullDashboardEventSink())
        self.tool_context = LiberoContext(primitives=FakePrims(),
                                          output_dir=OUT)
        self.advanced = []
        self.begin_calls = 0
        self.tool_context.advance = self._advance
        self.tool_context.begin_episode = self._begin_episode

    def _advance(self, name, args, primitive):
        self.advanced.append(name)
        self.tool_context.step_idx += 1
        return {"step": self.tool_context.step_idx,
                "libero_terminated": False, "result": primitive(**args)}

    def _begin_episode(self):
        self.begin_calls += 1
        self.tool_context.step_idx = 0
        return {"step": 0}

    def langchain_tools(self, *, no_images: bool = False,
                        resident: bool = False, vision: bool = False):
        return [*super().langchain_tools(no_images=no_images,
                                         resident=resident, vision=vision),
                *T.LIBERO_TOOLS,
                *(T.RESIDENT_TOOLS if resident else [])]


# A live sandbox so write protection on the archive is exercised for real.
sandbox.set_sandbox(SandboxPolicy(
    name="test-resident", source="inline", source_sha256="0",
    description="resident e2e test", read_roots=(OUT.resolve(),),
    write_roots=(OUT.resolve(),),
))

# Artifacts the rotation should carry into the archive.
(OUT / "states.json").write_text('[{"step_idx": 0}]')
(OUT / "world").mkdir(exist_ok=True)
(OUT / "world" / "world_00.npy").write_text("npy")

DIAGNOSIS = ("pi0 grasp closed on nothing because the prompt was name-only; "
             "next attempt uses a shape-descriptive prompt")
script = [
    AIMessage(content="attempt 1: direct grasp plan", tool_calls=[
        {"name": "move_to", "args": {"xyz": [0.1, 0.2, 0.3]}, "id": "c1"}]),
    AIMessage(content="grasping", tool_calls=[
        {"name": "pi0_pick", "args": {"prompt": "pick up the butter"},
         "id": "c2"}]),
    AIMessage(content="attempt 1 failed; resetting with diagnosis",
              tool_calls=[{"name": "reset_episode",
                           "args": {"reason": DIAGNOSIS}, "id": "c3"}]),
    AIMessage(content="drilling into the archived grasp", tool_calls=[
        {"name": "view_attempt_call", "args": {"attempt": 1, "seq": 2},
         "id": "c4"}]),
    AIMessage(content="wrapping up", tool_calls=[
        {"name": "finish",
         "args": {"status": "stuck", "summary": "test session"},
         "id": "c5"}]),
    AIMessage(content="done"),
]

print("=== resident surface ===")
tk = FakeToolkit()
exam_names = {t.name for t in tk.langchain_tools()}
res_names = {t.name for t in tk.langchain_tools(resident=True)}
check("exam surface has no resident tools",
      not ({"reset_episode", "view_attempt_call"} & exam_names),
      str(sorted(exam_names)))
check("resident surface adds exactly the two tools",
      res_names - exam_names == {"reset_episode", "view_attempt_call"},
      str(sorted(res_names - exam_names)))

print("\n=== scripted two-attempt session ===")
model = ScriptedModel(turns=script)
planner = DeepAgentPlanner(model="scripted", chat_model=model, resident=True,
                           dashboard_events=NullDashboardEventSink())
res = planner.solve(system_prompt="resident test", user_message="debug the cell",
                    toolkit=tk, max_turns=20)
check("no error", res.error is None, str(res.error))
check("finish captured", (res.finish_result or {}).get("status") == "stuck",
      str(res.finish_result))

print("\n=== rotation ===")
attempt_dir = OUT / "attempt_01"
check("attempt_01/ exists", attempt_dir.is_dir())
check("states.json moved into the archive",
      (attempt_dir / "states.json").exists()
      and not (OUT / "states.json").exists())
check("world/ moved into the archive",
      (attempt_dir / "world" / "world_00.npy").exists())
check("attempt video flushed into the archive",
      (attempt_dir / "episode.mp4").exists())
manifest = json.loads((attempt_dir / "attempt.json").read_text())
check("attempt.json records the diagnosis verbatim",
      manifest["reason"] == DIAGNOSIS and manifest["attempt"] == 1,
      json.dumps(manifest))
check("env was reset for the new attempt", tk.begin_calls == 1)
check("attempt counter advanced", tk.tool_context.attempt_no == 2)
policy = sandbox.active_policy()
check("archive is write-protected",
      any(str(p).endswith("attempt_01") for p in policy.write_denied),
      str(policy.write_denied))

print("\n=== per-attempt logs and seq restart ===")
archived = tool_log.load(attempt_dir)
check("archived log holds attempt 1's calls with call ids",
      [r["tool"] for r in archived] == ["move_to", "pi0_pick"]
      and [r.get("call_id") for r in archived] == ["c1", "c2"],
      json.dumps([(r["tool"], r.get("call_id")) for r in archived]))
live = tool_log.load(OUT)
check("live log restarts at seq 1 with the reset call",
      [r["seq"] for r in live] == [1, 2, 3]
      and [r["tool"] for r in live]
      == ["reset_episode", "view_attempt_call", "finish"],
      json.dumps([(r["seq"], r["tool"]) for r in live]))

print("\n=== drill-down ===")
drill = [m for m in res.messages
         if m.get("role") == "tool" and m.get("name") == "view_attempt_call"]
check("view_attempt_call returned the archived pi0_pick record",
      drill and "pi0_pick" in drill[0]["content"]
      and "grasp closed on nothing" in drill[0]["content"],
      drill[0]["content"][:200] if drill else "no tool message")

print("\n=== folding: what the model saw after the reset ===")
post_reset = model.seen[3]  # request that produced the view_attempt_call turn
folded = [m for m in post_reset if isinstance(m, ToolMessage)
          and m.tool_call_id in ("c1", "c2")]
check("archived tool results folded to digests",
      len(folded) == 2 and all("[attempt 1 seq" in str(m.content)
                               for m in folded),
      " | ".join(str(m.content)[:100] for m in folded))
check("digest carries the drill-down citation",
      any("view_attempt_call(attempt=1, seq=2)" in str(m.content)
          for m in folded),
      " | ".join(str(m.content)[:150] for m in folded))
check("digest is one line, not the raw result",
      all(len(str(m.content)) < 300 for m in folded),
      str([len(str(m.content)) for m in folded]))
reasoning = [m for m in post_reset if isinstance(m, AIMessage)]
check("model's own reasoning from attempt 1 stays",
      any("attempt 1: direct grasp plan" in str(m.content)
          for m in reasoning))
reset_msg = [m for m in post_reset if isinstance(m, ToolMessage)
             and m.tool_call_id == "c3"]
check("reset boundary message stays readable (not folded)",
      reset_msg and "archived_to" in str(reset_msg[0].content),
      str(reset_msg[0].content)[:150] if reset_msg else "missing")
pre_reset = model.seen[2]  # request that produced the reset turn
check("no folding before the first reset",
      all("[attempt" not in str(m.content) for m in pre_reset
          if isinstance(m, ToolMessage)))

print("\n=== transcript keeps the originals (folding is a request view) ===")
c2_transcript = [m for m in res.messages
                 if m.get("role") == "tool" and m.get("name") == "pi0_pick"]
check("transcript tool message is the original, not the digest",
      c2_transcript and "[attempt" not in c2_transcript[0]["content"],
      c2_transcript[0]["content"][:120] if c2_transcript else "missing")

print("\n=== truncation guard: resident survives empty turns, exam stops ===")
# Two consecutive EMPTY replies (the t5 shape: reasoning burned the whole
# output budget, nothing visible) followed by a proper finish.
trunc_script = [
    AIMessage(content=""),
    AIMessage(content=""),
    AIMessage(content="recovered", tool_calls=[
        {"name": "finish",
         "args": {"status": "stuck", "summary": "recovered after nudges"},
         "id": "t1"}]),
    AIMessage(content="done"),
]
tk_t = FakeToolkit()
model_t = ScriptedModel(turns=trunc_script, seen=[])
planner_t = DeepAgentPlanner(model="scripted", chat_model=model_t,
                             resident=True,
                             dashboard_events=NullDashboardEventSink())
res_t = planner_t.solve(system_prompt="s", user_message="go",
                        toolkit=tk_t, max_turns=20)
check("resident: recovered after two empty turns",
      (res_t.finish_result or {}).get("summary") == "recovered after nudges",
      str(res_t.finish_result))
check("resident: truncation nudge text was injected",
      any(isinstance(m, tuple) is False and "cut off by the output-token"
          in str(getattr(m, "content", "")) for m in model_t.seen[-1]),
      str([str(getattr(m, 'content', ''))[:40] for m in model_t.seen[-1]]))

tk_e = FakeToolkit()
model_e = ScriptedModel(turns=trunc_script, seen=[])
planner_e = DeepAgentPlanner(model="scripted", chat_model=model_e,
                             resident=False,
                             dashboard_events=NullDashboardEventSink())
res_e = planner_e.solve(system_prompt="s", user_message="go",
                        toolkit=tk_e, max_turns=20)
check("exam: still stops after ONE nudge (no recovery)",
      res_e.finish_result is None, str(res_e.finish_result))

sandbox.clear_sandbox()
print()
if failures:
    print(f"{len(failures)} CHECK(S) FAILED")
    sys.exit(1)
print("all checks passed")
