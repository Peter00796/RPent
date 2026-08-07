"""End-to-end check of DeepAgentPlanner with a scripted model (no API calls).

Drives the real planner, real middleware, real native tools and a real
LiberoContext; only the chat model and the env primitives are fakes.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/Users/yanxinpeng/Desktop/Spring2026/PRAxIs/RPent")
SCRATCH = Path(__file__).parent

from rpent.utils.logging import init_output_dir  # noqa: E402

OUT = init_output_dir(SCRATCH / "deep_agent_run")
# Per-run append-only logs: a leftover from a previous execution would read as a
# continuation of this one, which is the same trap begin_episode() now clears.
for _stale in ("tool_calls.jsonl", "analysis/entities.json"):
    (OUT / _stale).unlink(missing_ok=True)

from langchain_core.language_models.chat_models import BaseChatModel  # noqa: E402
from langchain_core.messages import AIMessage  # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatResult  # noqa: E402

import robots.libero.tools as T  # noqa: E402
from robots.libero.tools.context import LiberoContext  # noqa: E402
from rpent.dashboard.events import NullDashboardEventSink  # noqa: E402
from rpent.planner.deep_agent import DeepAgentPlanner  # noqa: E402
from rpent.planner.middleware import MIDDLEWARE_ORDER  # noqa: E402
from rpent.tools.toolkit import Toolkit  # noqa: E402


class ScriptedModel(BaseChatModel):
    """Replays a fixed list of AIMessages so the agent loop runs offline."""

    turns: list = []
    idx: int = 0
    seen_tool_counts: list = []

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kw):
        self.seen_tool_counts.append(len(tools))
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        msg = self.turns[min(self.idx, len(self.turns) - 1)]
        self.idx += 1
        return ChatResult(generations=[ChatGeneration(message=msg)])


def usage(i, o):
    return {"input_tokens": i, "output_tokens": o, "total_tokens": i + o,
            "input_token_details": {"cache_read": i // 2, "cache_creation": 10}}


class FakePrims:
    """Stands in for LiberoPrimitives; only the methods the script calls."""

    def move_to(self, **kw):
        return {"name": "move_to", "final_dist_m": 0.004}

    def pi0_pick(self, **kw):
        return {"name": "pick", "success": True, "chunks_used": 6}


class FakeToolkit(Toolkit):
    """A Toolkit whose LangChain surface is the real one, with fake primitives."""

    def __init__(self):
        super().__init__(dashboard_events=NullDashboardEventSink())
        self.tool_context = LiberoContext(primitives=FakePrims(), output_dir=OUT)
        self.advanced = []
        self.tool_context.advance = self._advance

    def _advance(self, name, args, primitive):
        self.advanced.append(name)
        self.tool_context.step_idx = len(self.advanced)
        return {"step": len(self.advanced), "libero_terminated": False,
                "result": primitive(**args)}

    def langchain_tools(self, *, no_images: bool = False):
        return [*super().langchain_tools(no_images=no_images), *T.LIBERO_TOOLS]


failures = []


def check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL':4}  {label}" + (f"\n        {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(label)


print("=== declared middleware order ===")
for name, role in MIDDLEWARE_ORDER:
    print(f"  {name:28s} {role}")

# ---------------------------------------------------------------------------
print("\n=== A. normal run: tools -> finish ===")
script = [
    AIMessage(content="localizing", tool_calls=[
        {"name": "back_project", "args": {"row": 10, "col": 20}, "id": "c1"}],
        usage_metadata=usage(1200, 60)),
    AIMessage(content="moving in", tool_calls=[
        {"name": "move_to", "args": {"xyz": [0.1, 0.2, 0.9], "gripper": 1.0}, "id": "c2"},
        {"name": "pi0_pick", "args": {"prompt": "grasp the yellow mug", "max_chunks": 8}, "id": "c3"}],
        usage_metadata=usage(1600, 90)),
    AIMessage(content="writing audit", tool_calls=[
        {"name": "finish", "args": {"status": "success", "summary": "solved"}, "id": "c4"}],
        usage_metadata=usage(1900, 40)),
    AIMessage(content="done", usage_metadata=usage(2000, 10)),
]
tk = FakeToolkit()
model = ScriptedModel(turns=script)
planner = DeepAgentPlanner(model="scripted", chat_model=model,
                           dashboard_events=NullDashboardEventSink())
res = planner.solve(system_prompt="You are the LIBERO agent.",
                    user_message="solve the task", toolkit=tk, max_turns=20)

# Assert the invariant (every tool the toolkit exposes reaches the model), not a
# magic count — hardcoding the number makes every new tool a spurious failure.
_expected = tk.langchain_tools()
check(f"all {len(_expected)} toolkit tools reach bind_tools",
      model.seen_tool_counts[0] == len(_expected),
      f"bound {model.seen_tool_counts[0]}, toolkit exposes {len(_expected)}")
check("perception tools include world_extent",
      "world_extent" in [t.name for t in _expected])
check("finish_result captured", res.finish_result == {"_finish": True, "status": "success", "summary": "solved"},
      str(res.finish_result))
check("advancing tools routed through ctx.advance", tk.advanced == ["move_to", "pi0_pick"], str(tk.advanced))
check("read-only tool ran without a context handle", any(
    m.get("role") == "tool" and m.get("name") == "back_project" for m in res.messages))
check("stats: turns/tool_calls", res.stats["turns_used"] == 4 and res.stats["tool_calls"] == 4,
      json.dumps(res.stats))
check("stats: usage accumulated", res.stats["total_input_tokens"] == 6700
      and res.stats["total_output_tokens"] == 200, json.dumps(res.stats))
check("stats: anthropic cache tokens captured",
      res.stats["cache_read_tokens"] == 3350 and res.stats["cache_write_tokens"] == 40,
      json.dumps(res.stats))
check("no error", res.error is None, str(res.error))
print("  transcript roles:", [m.get("role") for m in res.messages])

# ---------------------------------------------------------------------------
print("\n=== A2. tool_calls.jsonl — run evidence for read-only calls too ===")
from rpent.tools import tool_log  # noqa: E402

recorded = tool_log.load(OUT)
names = [r["tool"] for r in recorded]
check("every tool call recorded, in order",
      names == ["back_project", "move_to", "pi0_pick", "finish"], str(names))
check("read-only calls are present (states.json has none of these)",
      "back_project" in names)
check("seq is monotonic", [r["seq"] for r in recorded] == [1, 2, 3, 4],
      str([r["seq"] for r in recorded]))
check("args captured verbatim",
      recorded[1]["args"]["xyz"] == [0.1, 0.2, 0.9], json.dumps(recorded[1]["args"]))
check("result kept structured", isinstance(recorded[1]["result"], dict))
check("entity_index stripped from the record (already in entities.json)",
      all("entity_index" not in (r["result"] or {}) for r in recorded
          if isinstance(r["result"], dict)))
check("advancing vs read-only is computable from step_idx, not declared",
      recorded[0]["step_idx_before"] == recorded[0]["step_idx_after"]
      and recorded[1]["step_idx_after"] > recorded[1]["step_idx_before"],
      f"back_project {recorded[0]['step_idx_before']}->{recorded[0]['step_idx_after']}, "
      f"move_to {recorded[1]['step_idx_before']}->{recorded[1]['step_idx_after']}")
check("elapsed recorded per call", all("elapsed_s" in r for r in recorded))
check("log sits beside states.json, not inside analysis/",
      tool_log.path_for(OUT).parent == Path(OUT), str(tool_log.path_for(OUT)))

print("\n=== B. turn budget stops the run, exactly ===")


class NeverStops(BaseChatModel):
    """Always calls a tool, with a UNIQUE tool_call id per turn.

    Reusing one id across turns makes the graph stop after the first turn, which
    silently masks whether the turn budget works at all.
    """

    n: int = 0

    @property
    def _llm_type(self) -> str:
        return "never-stops"

    def bind_tools(self, tools, **kw):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.n += 1
        return ChatResult(generations=[ChatGeneration(message=AIMessage(
            content=f"turn {self.n}",
            tool_calls=[{"name": "move_to", "args": {"xyz": [0, 0, 1]}, "id": f"call_{self.n}"}],
            usage_metadata=usage(100, 10)))])


for limit in (1, 3, 8, 20):
    tk2 = FakeToolkit()
    m2 = NeverStops()
    p2 = DeepAgentPlanner(model="scripted", chat_model=m2,
                          dashboard_events=NullDashboardEventSink())
    r2 = p2.solve(system_prompt="s", user_message="go", toolkit=tk2, max_turns=limit)
    check(f"max_turns={limit}: exactly {limit} model turns, no recursion error",
          r2.stats["turns_used"] == limit and r2.error is None,
          f"turns={r2.stats['turns_used']} model_calls={m2.n} err={r2.error}")
    check(f"max_turns={limit}: finish_result is None when budget ran out",
          r2.finish_result is None)

# ---------------------------------------------------------------------------
print("\n=== C. --interactive is refused, not silently ignored ===")
import queue as _q  # noqa: E402
try:
    planner.solve(system_prompt="s", user_message="go", toolkit=FakeToolkit(),
                  max_turns=2, input_queue=_q.Queue())
    check("interactive raises NotImplementedError", False, "no exception")
except NotImplementedError:
    check("interactive raises NotImplementedError", True)

# ---------------------------------------------------------------------------
print("\n=== D. --no-images swaps read_image without changing the surface ===")
from langchain_core.utils.function_calling import convert_to_openai_tool  # noqa: E402

with_img = {t.name: convert_to_openai_tool(t) for t in tk.langchain_tools()}
no_img = {t.name: convert_to_openai_tool(t) for t in tk.langchain_tools(no_images=True)}
check("same tool names", sorted(with_img) == sorted(no_img))
check("read_image args_schema identical",
      json.dumps(with_img["read_image"]["function"]["parameters"])
      == json.dumps(no_img["read_image"]["function"]["parameters"]))
# The description must DIFFER: under --no-images the tool cannot do what the
# normal wording promises, and advertising a capability the run does not have
# costs the model a turn in a single-attempt episode.
d_on = with_img["read_image"]["function"]["description"]
d_off = no_img["read_image"]["function"]["description"]
check("read_image description is honest under --no-images",
      d_on != d_off and "DISABLED" in d_off and "segment" in d_off, d_off[:80])
check("every other tool's description is unchanged", all(
    with_img[n]["function"]["description"] == no_img[n]["function"]["description"]
    for n in with_img if n != "read_image"))

print()
if failures:
    print(f"{len(failures)} CHECK(S) FAILED")
    sys.exit(1)
print("all checks passed")
