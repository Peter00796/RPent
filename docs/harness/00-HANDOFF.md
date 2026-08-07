# Handoff — read this first

You are picking up an in-flight refactor of the agent harness in this repo. The
previous session left no memory of it; everything it knew that is not in the code is
in this directory. This file is the orientation. The other five are reference.

---

## What this work is

The LIBERO agent harness was rebuilt in two layers:

1. **Tools** — one 1931-line module became a package split by kind, and the tools are
   now **native LangChain tools** (`@tool` + Pydantic `args_schema` + `ToolRuntime`)
   instead of hand-written Anthropic schema dicts dispatched through a registry.
2. **Planner** — a new `--planner deepagents` drives them through LangChain's
   `create_agent` with a declared middleware chain, alongside the three pre-existing
   planners which were left untouched.

On top of that: three geometry tools (`world_extent`, `compare_extent`, and
principal-axis `shape` inside `segment`), an append-only **entity databus** that
relates readings across steps with staleness verdicts, a **tool-call log** so
read-only calls appear in the run's evidence, and a **cleansed system prompt** with
every per-cell answer and stale magic number removed.

## Where things stand

- Branch `refactor/langchain-native-tools`, HEAD `a1e75a1`, pushed to
  `Peter00796/RPent`. Working tree clean.
- 19 tools reach the model (14 LIBERO + 5 common). Regression tests pass.
- Remote sweep, prior-free, on the cleansed prompt: **8/10 on `libero_object_swap`
  t0-t9**. Two failures share one signature — see below.
- Model in use: **`deepseek-v4-flash`**, text-only. The planner is blind; SAM3 and the
  world maps see for it.

## Four things that will bite you immediately

1. **Never add `from __future__ import annotations` to
   `robots/libero/tools/agent_tools.py`.** LangChain resolves the `ToolRuntime`
   annotation to a real type; under PEP 563 it sees the string, injection silently
   fails, and every tool call dies **at dispatch, not at import**. Every other module
   in the repo has that import, so this is exactly what a tidy-up commit "fixes".

2. **macOS filesystems are case-insensitive.** A path typo differing only in case is
   the same directory. The previous session ran `rm -rf` on a mis-cased path and
   deleted the whole project tree; it survived only because everything was pushed.
   Push before destructive commands.

3. **SSH to github is blocked here** (port 22 intercepted by a VPN range). Push over
   HTTPS: `git push https://github.com/Peter00796/RPent.git <branch>`. `gh` is already
   the credential helper.

4. **`states.json` records only environment-advancing primitives.** On one examined
   run, 27 tool calls happened and `states.json` held 6. For anything about perception
   or file reads, read `tool_calls.jsonl`.

## What to do next

**Issue 1 in [04-open-issues.md](04-open-issues.md): the sandbox.** This is the
owner's stated priority and it is decided, not open for debate — implement it.

The problem: `rpent/tools/common.py::_resolve` does `get_repo_root() / path` with **no
sandbox**, so `read_text_file` can reach anything in the repo. Two standing
prohibitions ("never read the BDDL", "never read a prior solution to this cell") are
therefore prompt-enforced only, and a third file (`env_calibration.md`, 187 memorised
constants) is likewise only verbally blocked. On top of that, `ensure_resources`
re-downloads `RLinf/RPent-memory` over `resources/libero/` on **every run**, so
deleting the priors locally does not stick.

The shape the owner asked for, in their words: put the robot in a clean environment
each run.

```
--priors {none, memory, full}
```

| level | readable roots |
|---|---|
| `none` | `{output_dir}` only |
| `memory` | + `resources/libero/memory/`, `guides/strict_hybrid_guide.md`, `guides/pro_hybrid_guide.md` |
| `full` | + `results_*_pert/` — kept only as a comparison arm |

Plus: stop the HF sync overwriting, and note that the memory library itself still
ships `feedback_bowl_eef_y_offset.md`, holding a `+0.045` constant that measurement
has refuted. Cleansing the prompt did not clean the library.

**Then issue 2**, which you should not fix blind: two sweep runs spent every turn on
perception and issued zero motion commands (`segment` x14 and x24 respectively).
Read both transcripts on the box first. The distinction that decides the remedy is
whether the agent was *stuck* (re-segmenting the same thing) or *lost* (could not
ground the noun at all).

## How the owner works, and what they care about

Worth knowing before you propose anything, because these settled several arguments:

- **The point of the infrastructure is attribution** — being able to say what a
  component is worth in points, in tokens, and when it is harmful. Decisions get
  judged against whether they make attribution easier.
- **Mechanism over discipline.** A rule in a prompt is discipline; a gate in
  `wrap_tool_call` is mechanism. When both are possible, mechanism wins. Saying "we
  will write a rule telling the model not to cheat" will get pushed back on.
- **Heavy data on disk, references in context.** Point clouds and images never enter
  the prompt. Tools read paths and compute; the planner reasons over results and
  cites the path. The planner does **logical reasoning**, not data crunching — this is
  the deliberate contrast with code-as-policy approaches.
- **The tool layer is not to be rewritten.** It was judged the highest-quality part of
  the repo (perception/action separation, privileged-info withholding enforced in code
  rather than in the prompt, structured errors with fallbacks). Wrap it, extend it,
  do not restructure it.
- **Magic numbers are the enemy, but "contains a number" is the wrong filter.** The
  admission rule is two-dimensional: does it vary with the instance, and can a tool
  measure it. See [02-decisions.md](02-decisions.md) for the table. The owner has
  already run this ablation on their own cloud and found that removing magic numbers
  performed *better*, so this is settled by measurement, not taste.
- **Negative results get reported.** Several findings here are negative
  (`compare_extent` cannot separate success from failure; the whole-episode comparison
  is worthless). Do not quietly drop them.
- **Comparable project**: OpenMOSS/OpenETA (arXiv 2608.03924) covers much of the same
  governance ground with a different bet — learned grasp predictors and promoted grasp
  strategies rather than the planner reasoning over measured constraints. Worth
  reading before claiming novelty; several mechanisms there are better than ours and
  named in `02-decisions.md`.

## Verify you have not broken anything

```bash
PYTHONPATH=. python tests/harness/test_deep_agent.py   # planner end-to-end, no API key, no GPU
PYTHONPATH=. python tests/harness/test_databus.py
PYTHONPATH=. python tests/harness/test_shape.py
```

`test_deep_agent.py` drives the real planner, middleware, tools and context against a
scripted chat model. If it passes, the wiring is intact.

Audit any new run for prior leakage until the sandbox exists:

```bash
grep 'read_text_file' run.log | grep -E 'results_.*_pert|env_calibration'
```

A hit means that run consumed a per-cell answer and its result does not measure the
harness.

## Then read

[01-architecture.md](01-architecture.md) for the layout,
[02-decisions.md](02-decisions.md) before proposing a change (it records reversals, so
you do not re-litigate a discarded option), [03-findings.md](03-findings.md) for what
the real data showed, [05-operations.md](05-operations.md) for the boxes, log paths
and remaining gotchas.
