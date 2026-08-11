# Harness development notes

Working notes for the agent-harness refactor on branch
`refactor/langchain-native-tools`. Written for whoever picks this up next —
including a future session of the same assistant, which will not remember any of it.

**Start with [00-HANDOFF.md](00-HANDOFF.md).** It is the orientation: current state,
the traps that bite immediately, what to do next, and how the project owner works.
The rest is reference.

| File | What it holds |
|---|---|
| [00-HANDOFF.md](00-HANDOFF.md) | **Read first.** Orientation for a new session |
| [01-architecture.md](01-architecture.md) | What the harness is now, layer by layer, with file pointers |
| [02-decisions.md](02-decisions.md) | Every non-obvious decision and the argument that settled it |
| [03-findings.md](03-findings.md) | Measured findings — the evidence base, including defects found and fixed |
| [04-open-issues.md](04-open-issues.md) | What is not done, in priority order |
| [05-operations.md](05-operations.md) | How to run it, where the boxes and logs are, gotchas |
| [06-aspire-replication.md](06-aspire-replication.md) | ASPIRE (arXiv 2607.00272) replication checklist — the CaP arm is parked, see the banner |
| [07-handoff-20260811.md](07-handoff-20260811.md) | Session handoff: gate/replay/practice/resident, five generations, the t6 crack |
| **[08-draft-pr-narrative.md](08-draft-pr-narrative.md)** | **The change narrative for the PR** — every change from upstream in build order, code-grounded |
| **[09-baseline-table.md](09-baseline-table.md)** | **Every arm we have run**, its configuration, n, results and run-dir pointers; gaps as costed proposals |

## One-paragraph summary

The LIBERO tool layer was one 1931-line module; it is now a package split by tool
kind, and the tools are **native LangChain tools** (`@tool` + Pydantic schemas +
`ToolRuntime`) rather than hand-written Anthropic schema dicts dispatched through a
registry. A new `--planner deepagents` drives them through LangChain's `create_agent`
graph with a declared middleware chain. Three geometry tools were added on top of
`segment` (`world_extent`, `compare_extent`, plus principal-axis `shape` inside
`segment`), and an append-only **entity databus** relates readings across steps with
staleness verdicts. The system prompt was then cleansed of per-cell answers and stale
magic numbers, which cut it 42%.

## Project position

This work sits under the PRAXIS framing the project owner maintains separately
(`MINDSET.md`, not in this repo): the point of the infrastructure is **attribution** —
being able to say what a component is worth, in points, in tokens, and when it is
harmful. Several decisions only make sense against that goal; where that is the case
it is stated.

Two of that document's rules were repeatedly the deciding argument:

- **Mechanism over discipline.** A rule written into a prompt is discipline; a gate in
  `wrap_tool_call` is mechanism. Where both were possible, mechanism won.
- **Heavy data on disk, references in context.** Point clouds and images never enter
  the prompt. Tools read paths and compute; the planner reasons over the results and
  cites the path.

## Status at handoff

- Branch `refactor/langchain-native-tools`, pushed to `Peter00796/RPent`.
- 13 commits, from `340abf0` (tool split) to the handoff docs.
- Regression tests in [`tests/harness/`](../../tests/harness/) all pass.
- Remote sweep, prior-free, on the cleansed prompt: **8/10 on `libero_object_swap`
  t0-t9**. The two failures share a signature worth understanding before the next
  sweep — see `03-findings.md`.
