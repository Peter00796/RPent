# From upstream RPent to a self-growing harness — the change narrative

The account this branch's PR needs: what changed, in the order it was built, and
the argument that made each change necessary. Written to be checkable — every
structural claim carries a `file:line` and every empirical claim carries a run
citation in the project's `run:<dir>#seq=N` form.

**Branch point**: `3c2516e3` on `RLinf/RPent` main
(*"feat(dashboard): add sequential task session control (#69)"*).
**Head**: `14b62ae2`. 59 commits, 120 files, +17,174 / −2,518.
**Everything runs on `deepseek-v4-flash`**, text-only, `--no-images`. The planner
is blind by construction; SAM 3.0, the world maps and the geometry tools are its
only channel to the scene.

Read alongside [09-baseline-table.md](09-baseline-table.md), which holds every
number quoted here with its run directory.

---

## 0. The one-sentence claim, and what it is not

> A cheap, blind, text-only planner, wrapped in a harness that records its own
> evidence and grows its own memory under a gate, solves benchmark cells that
> the same model in the same environment could not solve before — and every step
> of how it learned to is citable to a single tool call.

Three things this is **not**, stated up front because the honest version is the
only one that survives a mentor:

1. **Not a comparison to a frontier model.** No head-to-head has ever been run.
   The only non-DeepSeek runs in the project are 10 opus and 3 glm runs from the
   pre-refactor era, on unmatched cells, with the answer key readable
   ([09 §3](09-baseline-table.md#3-pre-refactor-era-upstream-harness--our-prompt-of-the-time)).
   They prove nothing and are quoted nowhere.
2. **Not a growth curve.** The generational sequence 4 → 5 → 7 → 6 → 5 reads as
   growth and dies under repeats: `none` = 4, 6, 6 vs `memory@gen4` = 5, 8, 5,
   an effect of ≈ +0.7 cells against ±1.5 per-sweep spread at n=3
   ([09 §4.1](09-baseline-table.md#41-the-comparisons-that-are-actually-licensed)).
   The generational protocol is offered as **a measurement instrument that
   worked**, not as a positive result.
3. **Not a complete system.** The code-as-policy arm was built, produced no
   measured result, and is excluded from this branch (§11). One sweep pass was
   cut mid-run. One of three cross-seed exams failed. The environment's own
   checker is flaky on one cell. All below.

---

## 1. Tool layer: one module → a package of native LangChain tools

`340abf0d` · *refactor(libero): split tools.py and make the tools native
LangChain tools*

### 1.1 What upstream had

`robots/libero/tools.py` at the branch point is **1,930 lines**
(`git show 3c2516e3:robots/libero/tools.py | wc -l`) holding motion primitives,
the VLA bridge, SAM3 perception, geometry, state dumping, and the
hand-written Anthropic tool-schema dicts, all in one namespace. A tool call
reached its implementation through a five-hop chain: registry lookup →
spec dict → name string → `getattr` → `partial` → handler.

### 1.2 What it is now

A package split by tool kind, 4,481 lines across 15 modules — larger, because
the geometry that was previously implicit is now explicit and documented:

```
geometry.py   853   state.py    497   perception.py 472   agent_tools.py 456
schemas.py    405   motion.py   365   databus.py    310   tool_docs.py   304
context.py    261   vla.py      141   primitives.py 134   __init__.py    119
artifacts.py   93   legacy_specs.py 39   catalog.py    32
```

To be exact about the arithmetic: 1,930 → 4,481 is **not a pure split**. The
package also added concerns that did not previously exist as code —
`databus.py`, `context.py`, `schemas.py`, `tool_docs.py`, `catalog.py`,
`artifacts.py`.

The tools are **native LangChain tools**: `@tool` + a Pydantic `args_schema` +
a `ToolRuntime` parameter carrying the live context. A whole tool, start to
finish (`robots/libero/tools/agent_tools.py:236`):

```python
@tool(args_schema=Pi0PickInput, description=tool_docs.render_description("pi0_pick"))
def pi0_pick(prompt: str, runtime: ToolRuntime, max_chunks: int = 24,
             lift_thresh: float = 0.05, gripper_closed_thresh: float = 0.06) -> dict:
    """Model-facing text renders from ``tool_docs`` — edit it there."""
    ctx = _context(runtime)
    return ctx.advance("pi0_pick", {...}, ctx.primitives.pi0_pick)
```

Dispatch is two hops — the `@tool` function, then `ctx.advance`, then the
primitive. No name-string `getattr`, no `partial`, no `execute_tool` lookup
table.

**Why this is not cosmetics.** `ctx.advance`
(`robots/libero/tools/context.py:173`) becomes the single seam every
environment-advancing call passes through, and it owns *all* the per-action
bookkeeping: timing, cancellation, the action-video frame slice, the `step_idx`
increment, the databus staleness downgrade, the `states.json` dump, and
rendering the new state back to the planner. No tool re-implements any of it,
and no tool can forget it. That is what later makes the evidence layer (§5), the
attempt rotation (§8) and the sandbox's write protection (§4) possible **as
mechanisms** rather than as conventions. A five-hop dispatch has five places to
forget.

It also became the natural home for a fix the evidence layer surfaced — the
terminal-episode guard (`context.py:192`):

```python
# A finished episode cannot step again — the env client asserts on it.
# Surface it as information instead of a crash: experiment episodes in
# particular keep probing after an accidental solve, and one late motion
# call must not cost the run its notes.
```

And the vocabulary of "which calls mutate the world" is a 32-line,
dependency-free module (`robots/libero/tools/catalog.py`) that **cannot drift**:
`agent_tools.py:448` raises at import if its `ADVANCING_TOOLS` list disagrees
with `catalog.PRIMITIVE_TOOL_NAMES`.

### 1.3 Three decisions in this layer that a reviewer will otherwise re-litigate

- **`agent_tools.py` must never gain `from __future__ import annotations`.**
  LangChain detects the `ToolRuntime` parameter by resolving the annotation to
  a real type; under PEP 563 it sees the string, injection silently fails, and
  every tool call dies **at dispatch, not at import**. Every other module in the
  repo has that import, so this is precisely what a tidy-up commit "fixes".
  Verified against langchain-core 1.5.3 / langgraph 1.2.10 with a two-file
  reproduction ([02-decisions](02-decisions.md)).
- **Schemas are Pydantic, and that was a reversal.** The first adapter passed
  the existing JSON Schema dicts through byte-identically so the model-facing
  surface could be *proven* unchanged across the migration (it hashed to
  `c646df3d…` before and after). The owner reversed it: one definition should
  give validation, schema and types. Cost accepted and recorded — the rendered
  schema shape changed, so that hash is void. Trap that cost real time: Pydantic
  `list[float]` needs explicit `min_length`/`max_length` or the array-length
  constraint silently disappears.
- **`agent_tools.py` stays a separate namespace.** 9 of 14 tools wrap mixin
  methods, and `@tool` cannot decorate a method (`self` becomes a tool
  argument). Collapsing them would force renaming every physics function so the
  tool could own the good name. Two namespaces, both names correct; net saving
  would have been one file. The corollary is the module-qualified import style
  (`perception.back_project(...)`, `agent_tools.py:31`): **five** tool names
  collide with their handler names (`view_driver_state`, `view_camera_meta`,
  `back_project`, `world_extent`, `compare_extent`), and a `from … import`
  would be shadowed by the `@tool`-decorated function, making the body call a
  non-callable `StructuredTool`.

### 1.4 Convergence with upstream, worth saying out loud

Upstream has since done its own version of part of this: `#73`
*feat(env): manage env state centrally* adds `rpent/tools/state.py` (332 lines,
a per-run `EnvState` owning `states.json` and artifact storage) and a
`@readonly` decorator in `rpent/tools/toolkit.py` so that handlers capture a
fresh observation **by default** and observational tools opt out. That is the
same instinct as our advancing/read-only split, arrived at independently. The
difference in destination is the point of §5: they centralized *state capture*;
we centralized the *evidence record*, including the calls that change nothing.

---

## 2. Model-facing text has exactly one source

`d6f9faad` · *refactor(tools): single-source structured tool descriptions +
leak lint*

Everything the model reads about a tool now lives in two files:

- `robots/libero/tools/tool_docs.py` (304 lines) and its common-tool twin
  `rpent/tools/tool_docs.py` — descriptions authored as **structured entries**
  and rendered deterministically by `render_doc`
  (`rpent/tools/tool_docs.py:210`). `agent_tools.py` injects the rendered string
  via `@tool(description=…)`; the Python docstrings are dev notes and say so.
- `robots/libero/tools/schemas.py` — each argument's text is its
  `Field(description=…)`, with the module header stating the consequence:
  *"Field descriptions are part of the model-facing surface … treat edits here
  the same as edits to a prompt."*

The template is six fields, and the boundaries between them are the interesting
part (`rpent/tools/tool_docs.py:10`):

| field | rule |
|---|---|
| `what` | one sentence, verb-first (the only required field) |
| `need` | **preconditions only** — never restate arguments; those live in the schema and nowhere else |
| `returns` | field semantics, units, which returned fields to trust when |
| `when` | local selection vs a sibling tool — **never a workflow position**; procedure ordering is owned by the system prompt |
| `how` | call forms for *this* tool — **no multi-step procedures spanning other tools**, "that is how recipes creep back into tool descriptions" |
| `failure_modes` | how it goes wrong; *"quantitative caveats here must have measurement backing"* |

Content was migrated **verbatim** from the pre-migration docstrings — moved into
fields, not reworded — because *"the model-facing surface is an experiment
variable: a wording change here must be made deliberately and measured, never
smuggled in with a refactor."*

The reason all of this is worth the ceremony is attribution. The model-facing
surface has to be a *surface* — hashable, diffable, lintable — not a scattering
of docstrings. `tests/harness/test_tool_docs.py` (177 lines, stdlib-only, loads
the LIBERO docs module **by file path** so it lints without importing langchain)
is what keeps it one. Its checks:

1. **Import-time validation** — unknown keys are fatal, `what` is required
   (`validate_docs`, `rpent/tools/tool_docs.py:238`).
2. **The roster is hand-maintained** (`KNOWN_TOOL_NAMES`), so a rename or
   removal breaks the test visibly instead of leaving dangling references.
3. **Documented set == real surface**, checked symmetrically with `^`, so both
   a documented-but-nonexistent tool and an undocumented one fail.
4. **The prior-leak lint**, over the *rendered* bytes the model actually sees:
   ```python
   FORBIDDEN_PATTERNS = [r"resources/", r"results_\w*", r"env_calibration",
                         r"guides/", r"past recipe", r"memory file",
                         r"memory librar", r"MEMORY\.md"]
   ```
5. **The dangling-backtick lint** — every `` `identifier` `` in a description
   must be a real tool or a whitelisted argument name, so a rename cannot leave
   the model chasing a tool that no longer exists.
6. **Byte-identity across both substrates** — the legacy Anthropic spec dicts
   and the native LangChain tools must both equal the rendered source, for both
   doc packages. That is the anti-drift proof.

The division of labour with the prompt is stated and enforced: **the prompt says
when and why** (procedure, regime, invariants no tool reports); **the tool
description says what and with which caveats**. Before, `|Δxy| > 0.30` appeared
in both. Now the tool description owns it — and it owns it as a measured fact,
not advice: *"NEVER command a single `move_to` with |Δxy| > 0.30 — OSC flips IK
and the run corrupts"* (`robots/libero/tools/tool_docs.py:52`).

There is one more pattern here that recurs everywhere below: **a capability that
varies with a runtime flag gets its own docs entry, never a static superset
description.** Under `--no-images`, `read_image` is swapped for
`read_image_text_only`, which advertises the truth rather than promising
something it cannot do.

---

## 3. Prompt cleansing, then capability leveling

Two separate commits on purpose, because they are two different injection
channels and each must be attributable on its own.

### 3.1 Cleansing — `5530ca55`, `6e8b8577`

The upstream-era prompt contained per-task `t0`–`t9` recipe blocks with their
coordinates. `robots/libero/prompts/system.py` measured **33,463 bytes** before
`5530ca55` and **19,544 bytes** after; the rendered prompt went 36,891 → 21,517
chars ([01-architecture](01-architecture.md)). What was deleted:

- the per-cell recipe blocks and all their coordinates — including, verbatim in
  the old file, a `t4 SINGLE-ATTEMPT LEVERS (READ — the seed-0 …)` section;
- `KEY_HYPERPARAMETERS` — per-object thresholds duplicating tool-schema
  defaults, plus scene-specific eef heights;
- `eef_y = plate_y + 0.045` — a single measurement promoted to a constant, which
  measurement later refuted (offsets ranged 1.0–4.1 cm *within one run*,
  [03-findings](03-findings.md));
- WORKFLOW step 3, *"read the seed-0 reference"* — the leak channel itself;
- and, in `6e8b8577`, the injection of `env_calibration.md`: 187 numeric
  constants under headings like *"OSC reachable workspace"* and *"Object-level
  reference heights"*, a probe log turned into a lookup table, with
  `libero_10_with_mug t0` named directly. The object heights it held are now
  `segment().shape.height_m`.

**The admission rule that decided each case is two-dimensional**, and "contains a
number" is not it — that filter is wrong in both directions. A drawer's In-region
bounds are numeric, invariant and not perceptually recoverable: that is
knowledge. *"The dark bottle is the salad dressing"* has no numbers and is pure
answer.

|  | varies with the instance | invariant |
|---|---|---|
| **a tool can measure it** | never in the prompt — measure it | at most a check, never a value |
| **no tool can recover it** | this is the cheat (a cell's answer) | **the only class worth its tokens** |

What survived: frame conventions (`+y = robot-LEFT`), gripper semantics, which
primitive threads an IK singularity, the wrist camera's modality weakness, and
`move_to` stalling being a failure at `final_dist_m > 0.02`.

### 3.2 Leveling — `af2dfef3`

Cleansing removed answers. Leveling removed the *advertising*. The prompt varies
with what the sandbox actually permits, never with a profile name. Three
capability booleans — `memory`, `playbook`, `resident`
(`robots/libero/prompt_bundle.py:10`) — and the call site probes the live policy
object (`rpent/cli/main.py:338`):

```python
memory_on = memory_exposed(env_name)                  # reads _POLICY, not args
…
# Readable AND existing: advertising an empty root cost the agent a
# confused list_dir on the first playbook-less practice run.
playbook_on = sandbox_policy.can_read(task_dir) and task_dir.is_dir()
system_prompt = prompt_bundle.render("system", variables=prompt_vars,
    memory=memory_on, playbook=playbook_on, resident=args.resident)
```

`memory_exposed` (`rpent/tools/sandbox.py:182`) asks the *policy* whether the
library roots are readable — *"a capability read off the live policy, never a
profile name, so prompt and enforcement cannot disagree."* A custom profile that
exposes the library gets the library instructions automatically, whatever it is
called.

The consequence the owner insisted on, and the one that most surprises readers:
**every verbal file prohibition was deleted, in every variant.** The old ⛔
blocks (*"do NOT read `results_*`"*, *"do NOT read `env_calibration.md`"*) were
discipline standing in for a missing mechanism. Once the sandbox exists they
become pure advertisement — *naming a blocked file tells the model it exists and
what is in it*. The prior-free prompt now reads as if those files never existed.

That is a lint, not a metaphor. `tests/harness/test_prompt_leveling.py` runs 44
assertions over four rendered variants; the load-bearing one is a vocabulary
that must never appear in **any** variant (`:47`):

```python
# Naming any of these is a prior leak, in EVERY variant: the sandbox blocks
# them, so the prompt must not acknowledge they exist.
LEAKS_ALWAYS = [r"resources/", r"results_\w*", r"env_calibration",
                r"guides?/", r"hybrid_guide", r"MEMORY\.md"]
LEAKS_PRIOR_FREE = [r"memor(y|ies)", r"skill librar"]
```

plus `re.search(r"do not read", text) is None`, and the reverse direction —
the exam variants must not contain the strings `reset_episode`,
`view_attempt_call` or `attempt_`, *"because the tool is absent there, so naming
it would advertise a capability the run lacks"* (`:107`).

The same rule governs the resident regime: a prompt that forbids resetting while
the tool list ships `reset_episode` advertises a false boundary, so the resident
variant **replaces** the ⛔ SINGLE-ATTEMPT block rather than adding to it
(`robots/libero/prompts/system.py:29` `_REGIME_EXAM` vs `:40`
`_REGIME_RESIDENT`, assembled at `:411`).

Rendered sizes of the leveling ladder, measured at head with the test's own
variable bindings:

| variant | system | user | total |
|---|---|---|---|
| `none` | 19,586 | 965 | 20,551 |
| `memory` | 20,240 | 1,031 | 21,271 |
| `+ playbook` | 20,471 | 1,031 | 21,502 |
| `+ resident` | 20,928 | 1,031 | 21,959 |

The library step costs 654 system chars, the playbook line 231, the resident
regime swap +457 — i.e. **the whole capability ladder is under 7% of the
prompt**, which is what makes it a clean attribution axis.

Note the vision channel is *not* leveled here: it is leveled one layer down, at
the tool surface (§9), the same mechanism-not-prohibition pattern applied to
tool existence rather than prompt text.

---

## 4. The sandbox: fail-closed, profiles as data, code owns the invariants

`a22baab3` · *feat(sandbox): always-on file sandbox with declarative profiles*
· with `f4a36c72` fixing the fingerprint

This is the change that makes every number after it mean something.

### 4.1 The problem, measured before it was fixed

`rpent/tools/common.py::_resolve` did `get_repo_root() / path` with **no
boundary**, so `read_text_file` could reach anything in the repo. Three standing
prohibitions were prompt-enforced only. And `ensure_resources` called
`snapshot_download(repo_id="RLinf/RPent-memory", local_dir=resources_dir.parent)`
**on every run**, overwriting `resources/libero/` — so deleting the priors
locally did not stick, and any locally curated memory was clobbered. One run's
sync died with `429 Too Many Requests`, the exception was swallowed, and the run
continued on a *partially* updated `resources/`.

Since what lives on that HF repo *is* the magic-numbers-and-priors payload, the
sync was not a convenience: **it was the delivery mechanism for exactly what the
prompt cleansing had removed.**

The scale of the leak, counted from `run.log` across every run ever made
([09 §2](09-baseline-table.md#the-prior-leak-audit-measured)):

| era | n | read `results_*_pert` (a cell's answer) | read `env_calibration.md` |
|---|---|---|---|
| pre-refactor | 155 | **104 (67%)** | 89 |
| this framework, pre-sandbox | 11 | 1 | 11 |
| this framework, sandbox on | **136** | **0** | **0** |

### 4.2 The four design commitments

**Always on.** There is no `--sandbox off`. Debugging without a boundary is
`configs/sandbox/unrestricted.yaml` — a fingerprinted state whose runs
self-identify as measuring nothing. Until `set_sandbox()` runs, every check
**fails closed** (`rpent/tools/sandbox.py:196`):

```python
def check_read(p: Path) -> None:
    if _POLICY is None:
        raise SandboxDenied(
            "sandbox not initialised: no file access is available "
            "(main.py sets it from --sandbox; call set_sandbox() in scripts)")
    _POLICY.check_read(p)
```

A leak must not be reachable by forgetting a flag. Every reader goes through it
— `read_text_file` (`rpent/tools/common.py:86`), `write_text_file` (`:103`),
`list_dir` (`:114`), `view_attempt_call` (`:139`), `read_image`
(`rpent/tools/langchain_common.py:140`), `inspect_image`
(`rpent/tools/vision.py:137`) — and the check precedes the existence test, so a
denial cannot be used as a file-existence oracle.

**Profile = shape, env = binding.** Profiles reference placeholders
(`{output_dir}`, `{memory_common}`, `{memory_env}`, `{memory_task}`,
`{staging_root}`, `{repo_root}`) and `default_bindings()` (`sandbox.py:218`)
resolves them per run from `--env`, so one `memory.yaml` serves libero and
whatever comes next and "the memory arm" stays the same experimental condition
across environments. Code never special-cases a profile name; the YAML is the
whole story, and unknown keys are fatal (`_ALLOWED_PROFILE_KEYS`,
`sandbox.py:55`). The whole of `configs/sandbox/none.yaml`, the gen-0 control
arm:

```yaml
name: none
description: run workspace only — no priors of any kind
read_roots:  ["{output_dir}"]
write_roots: ["{output_dir}"]
```

**Config declares intent; code owns invariants.** `write_denied` is not in the
allowed key set — *it cannot be declared in config at all.* It is derived from
`ARTIFACT_LAYOUT` (`robots/libero/tools/artifacts.py:55`):

```python
def protected_paths(output_dir) -> tuple[Path, ...]:
    """… Derived from ``ARTIFACT_LAYOUT`` so a new artifact kind is
    protected by construction, not by remembering."""
    names = {template.split("/")[0] for template in ARTIFACT_LAYOUT.values()}
    return tuple(sorted(Path(output_dir) / name for name in names))
```

and registered by the toolkit at construction, `sandbox.json` included so the
fingerprint protects itself (`robots/libero/toolkit.py:52`). *An agent that can
rewrite its own evidence log invalidates every attribution claim*, so that
boundary is not configuration. `write_roots` is `{output_dir}` alone in **every**
shipped profile, `unrestricted` included; the memory library is reachable only
through the promotion gate, and agent proposals land in
`{output_dir}/memory_proposals/`.

**The sync is opt-in and staged.** `ensure_staged_priors`
(`rpent/utils/resources.py:28`) replaces `ensure_resources`. Three ways it
downloads nothing: the profile does not reference `{staging_root}` (only
`full.yaml` does, and `enabled` comes from `sandbox_policy.uses_staging`, not
from a flag — `rpent/cli/main.py:312`); `HF_HUB_OFFLINE=1`; an existing staging
copy is reused. The target is `.staging/<env>/`, never `resources/`. And there
is deliberately **no `try/except` around `snapshot_download`** — a partial sync
raises out of `main()` rather than warning and continuing, because a comparison
arm on a silently partial payload measures nothing.

`read_image` is sandboxed too: without the check it is a generic byte
exfiltration channel (any file, base64, straight to the model), not an image
viewer. So is `inspect_image` later (§9), and so is `view_attempt_call` (§8).

### 4.3 The "delete the old memory docs" story

The sandbox is only half of it. The memory library that shipped on HF still
contained `feedback_bowl_eef_y_offset.md` — the `+0.045` constant measurement
had refuted. *Cleansing the prompt did not clean the library.* The resolution
was not to edit the old library: it was to stop injecting it, and **rebuild a
new one clean-room from zero under gate control** (§6). `memory/` at head holds
21 general entries and 9 task-playbook entries, none of which existed before
2026-08-07, and every one of which carries the run citations it was mined from.

Fingerprint of an actual run, for the reviewer who wants to check an arm:

```json
{ "profile": "memory",
  "source": ".../configs/sandbox/memory.yaml",
  "source_sha256": "6c44078c28bac3e550e692306662d2d5b75b57ac54b2d3af7b257cb80981771c",
  "read_roots":  ["…/<run_dir>", "…/memory/common", "…/memory/libero"],
  "write_roots": ["…/<run_dir>"],
  "write_denied": ["…/states.json", "…/tool_calls.jsonl", "…/world", …],
  "uses_staging": false }
```

---

## 5. The evidence layer: every call, joined, and replayable from disk alone

`a80aca56` (tool-call log) · `41b7f11f` (databus) · `f12f0a39`–`3e509911`
(replay)

### 5.1 `tool_calls.jsonl` — the read-only calls are the point

`states.json` records only environment-**advancing** primitives. On one examined
run, 27 tool calls happened and `states.json` held 6. Everything about
perception and file reads — including whether the agent read a prior — was
invisible.

`ToolCallLogMiddleware.wrap_tool_call` (`rpent/planner/middleware.py:249`)
writes one line per call. Universality is structural, not a policy: the hook
wraps the *dispatcher*, so there is no name filter and no `if advancing:` branch
— a read-only `segment` or `list_dir` takes exactly the same path as `move_to`.
The `except` branch logs `status="raised"` **and re-raises**, so a tool that
crashes still leaves a record. And `step_idx` is sampled on both sides of
`handler(request)`, so a read-only call records equal indices and is thereby
pinned to the env state it observed.

The on-disk record (`rpent/tools/tool_log.py:78`):

```python
record = {"schema_version": …, "seq": _SEQ, "tool": tool, "args": args or {},
          "status": status, "elapsed_s": …,
          "step_idx_before": step_idx_before, "step_idx_after": step_idx_after,
          "result": rendered}
if call_id:
    record["call_id"] = call_id
```

*"`step_idx` is captured before and after each call, so whether a call advanced
the environment is **computed from the log rather than declared in it** — and a
read-only call is pinned to the env state it observed."* Three details that
matter: appends are under a module lock (a turn's tool calls run concurrently,
so the sequence would not be monotonic without one); the writer **never raises**
(*"a missing log line is a smaller loss than a failed episode"*); and
`rpent/tools/tool_log.py` is **stdlib only**, deliberately, because diagnostics
must be able to read a run without importing the agent framework.

The `call_id` field exists because of a bug that had not happened yet. When the
attempt-folding middleware (§8) needed to align message-list entries with log
records, position-based alignment was rejected — parallel calls in one turn can
land in the log in a different order than in the message list, and a
misattributed `seq` in a digest is worse than no digest.

Middleware order is a declared constant, not an emergent property, because *a
different order is a different method* (`rpent/planner/middleware.py:53`):

```python
MIDDLEWARE_ORDER = (
    ("ModelCallLimitMiddleware",   "turn budget (prebuilt: langchain)"),
    ("TranscriptMiddleware",       "transcript + usage + dashboard projection"),
    ("ToolCallLogMiddleware",      "run-evidence record of every tool call"),
    ("AttemptFoldingMiddleware",   "resident sessions only: …"),
    ("ToolCallIntegrityMiddleware","innermost: repair orphan tool_calls pre-flight…"),
    ("InjectionLedgerMiddleware",  "not implemented — per-component token accounting"),
    ("GateMiddleware",             "not implemented — hard gates + shadow mode"),
    ("ProvenanceMiddleware",       "not implemented — argument-level evidence"),
    ("CompactionMiddleware",       "not implemented for exam runs — env-unsafe, and cache-hostile…"),
)
```

The four "not implemented" entries are named on purpose: they are the known
gaps, and naming them is cheaper than rediscovering them.

### 5.2 The entity databus — append-only, and it never resolves a conflict

`robots/libero/tools/databus.py` (310 lines) relates readings of the same named
entity across steps. Three commitments:

- **Append-only, never a mutable "current position."** A mutable current value
  destroys the provenance `world_path` exists to provide — a motion could no
  longer cite the reading it was planned from. Averaging is deliberately not
  offered: two readings of a container's near wall have biases that may cancel,
  but two readings that caught an object's *body* and its *cap* average to a
  point on neither. A reducer has to know what it reduces, so reduction stays an
  explicit tool.
- **Staleness is computed by the harness, interpreted by the planner.** Four
  verdicts (`databus.py:49`) — `fresh`, `unverified`, `possibly_bumped`, `held`
  — assigned by measured distance from the eef path
  (`mark_after_motion`, `databus.py:185`). *"The harness can say 'the
  end-effector passed within 6 cm of where you last saw this'; only the planner
  can decide whether that matters for the next command."* The bump radius is
  deliberately generous, and the docstring says why: *"a false
  `possibly_bumped` costs one re-`segment`, while a missed one can cost the
  episode."* Documented approximation, in the function's own docstring:
  proximity is tested against the straight segment between the eef poses before
  and after, so `pi0_pick`'s descent-and-lift is invisible to it — **the verdict
  is a lower bound on disturbance**, and `unverified` means *"not known to have
  been disturbed"*, never *"known to be untouched."*
- **Conflicts are reported, never resolved.** `identity_warning`
  (`databus.py:122`): the same entity's new reading is > 5 cm from the last one
  *and* nothing had marked that one as disturbed — either the object moved or
  this mask is a different object with the same appearance. `collision_warning`
  (`databus.py:141`): two *different* names land within
  `COLLISION_RADIUS_M = 0.03`. The 3 cm comes from data, in the constant's own
  comment: *"Tabletop objects measured 6-20 cm apart on real scenes, and a
  single object's readings agreed to millimetres, so 3 cm separates the two
  cases with room to spare."* And the detector states the limit of its own
  reach in the same comment block: *"this catches a collision, not a swap. Two
  entities at two distinct positions with their labels exchanged are
  geometrically self-consistent, and no measurement here can separate them."*
  The remedy it recommends is epistemic rather than computational — corroborate
  with an independently-phrased query for a *discriminating attribute* rather
  than the name.

### 5.3 Replay is a completeness test wearing a UI

```bash
PYTHONPATH=. python -m rpent.replay <run_dir>    # -> replay.html
python scripts/replay_run_3d.py <run_dir>         # -> 3D point-cloud slider
```

Replay rebuilds a finished run as a turn-by-turn timeline **from the disk
artifacts alone**, and renders its own incompleteness as a first-class block:
twelve distinct warning sites feed `RunReplay.warnings`, which the HTML surfaces
under the heading **`record gaps`** (`rpent/replay/html.py:131`) and the CLI
prints to stderr. That is the constraint working as designed — a gap means the
*logs* are missing something, and the fix is to record more, not to patch the
renderer.

`loader.py` treats `tool_calls.jsonl` as ground truth and the transcript as a
contributor of reasoning text. The join is **positional with a name check**, and
it degrades loudly rather than silently (`rpent/replay/loader.py:159`):

```python
if block.get("name") and block["name"] != call.tool:
    warnings.append(f"seq {call.seq}: transcript says {block['name']!r}, "
                    f"log says {call.tool!r} — positional join may be off here")
```

The `advanced` property (`loader.py:36`) is where §5.1's before/after design
cashes out: *"Computed from the log, not declared (the `tool_calls.jsonl`
contract)."*

`render.py` holds one renderer per tool in a `REGISTRY` (`:329`) — adding a tool
means adding a function — with a firewall so *"a broken renderer must not sink
the replay"* (`:349`). Renderers only **read**: *"a replay must never compute new
evidence, only display what the run recorded"*, and the single allowed
derivation is `project.py` turning a recorded world-xyz into a dot on the
recorded camera image by nearest-neighbour lookup in the stored world maps. No
camera math, and a projection whose error exceeds `VISIBILITY_ERR_M = 0.05` is
drawn as a warning line, never a dot — *"an occluded point must not look like a
confident one."* Every call anchors as `#seq-N`, the deep-link format the gate
and the memory library cite. Stdlib + numpy only.

### 5.4 What the evidence layer caught that nothing else would have

- **`pi0_pick.success` is false precisely when pre-positioning is good.** Its
  predicate requires ≥ 10 cm of descent; on a successful run the agent had
  pre-positioned at z=0.20 with the bottle top at 0.146, so descent was 8.8 cm
  and `success=False` on a grasp that worked. *The flag penalises the behaviour
  the prompt teaches.* That run survived only because the agent verified
  geometrically instead.
- **Gripper width does not detect a grasp.** One run held 0.047 for five
  consecutive steps while the point cloud found nothing below the eef for the
  first three and 18k/20k points for the last two.
- **`world_extent(mode="held_object")` was reporting the tabletop as a grasped
  object** — of 25 closed-gripper steps across six runs, **12 were readings of a
  surface**.
- **Mask edge-bleed inflated every `shape` extent, up to 6×** (a soup can read
  0.398 m untrimmed, 0.067 m trimmed).
- **`compare_extent` cannot separate success from failure.** Four releases: the
  signature was indistinguishable between the two runs that solved and the two
  that never terminated, because an object perched on the rim registers like a
  seated one. Reported as a negative result and written into the tool's own
  contract.

---

## 6. The promotion gate, and the generational protocol

`92ee8e30` · *feat(gate): the promotion gate — layered digestion from run
records to library commits*

```bash
python -m rpent.gate observe    RUN...            # per-run, LIBRARY-BLIND (LLM)
python -m rpent.gate synthesize RUN...            # sweep-wide proposals + HARNESS_REVIEW.md (LLM)
python -m rpent.gate review     RUN... --proposals <dir>   # five mechanical checks
#   human edits verdicts.yaml                     <- the interrupt
python -m rpent.gate apply      verdicts.yaml     # the ONLY writer of memory/
python -m rpent.gate ledger     RUN...            # consumption track record per entry
```

**Layered digestion**: observers see exactly what one run recorded and nothing
else, so support for a claim can be counted from *independent* discovery; the
synthesizer sees everything (observations, outcomes, the current library, the
ledger) and triages each cluster into `add` / `revise` / `evict` / `endorse`,
plus a human-facing memo for what a memory entry cannot fix.

**The iron rule against hearsay** (`rpent/gate/__init__.py:23`): *"proposal
evidence grounds to `run:<name>#seq=N` tokens (resolved straight into
`tool_calls.jsonl`), never to observation files. Observations are the
synthesizer's index, not evidence."* One grammar, one regex
(`rpent/gate/tokens.py:26`):

```
run:<run_dir_name>#seq=17      one tool call   -> tool_calls.jsonl record
run:<run_dir_name>#step=5      one env step    -> states.json entry
run:<run_dir_name>/<relpath>   one artifact    -> file under the run dir
```

`resolve()` (`tokens.py:58`) dereferences a `#seq=` token into the actual logged
record and returns the tool name, its args, its status and a truncated result —
so the reviewer reads *what the record says*, not what the proposal claims it
says — plus a `replay.html#seq-N` deep link. A proposal with no evidence is
rejected at the contract stage with the reason spelled out
(`rpent/gate/proposal.py:102`): *"no evidence — a proposal without citations is
not read."*

The five checks are five labelled sections of one pass, `run_checks`
(`rpent/gate/checks.py:117-225`), each tagging its findings with its own name:

1. **contract** — every cite must dereference; a `revise`/`evict` gets an
   automatic flag to verify the cited records show the entry was *consumed and
   still failed*. If anything rejects here the pass **short-circuits**: *"unevaluable; the other checks would just add noise."*
2. **numbers** — every number in the prose must appear, to rounding tolerance,
   in some cited record, or: *"either cite the measurement or delete the
   number."* Integers below 10 are exempt as prose.
3. **cell answers** — tier-aware. At `scope=task` naming this cell's objects is
   the tier's whole point, so only *absolute coordinate triples* are flagged
   (*"they die with the seed"*). At `common`/`env`, any token matching a real
   entry in the cited runs' own `states.json` `object_names` is flagged as *"an
   answer, not knowledge"* — the forbidden vocabulary is **measured from the
   runs**, not hard-coded.
4. **scope** — a `scope=common` claim that names the environment or one of its
   objects is probably `scope=env`.
5. **dedup** — Jaccard ≥ 0.50 against the existing library ("consider
   endorse/revise instead of add"), ≥ 0.70 against sibling proposals in the
   batch ("merge and count support").

Plus a sixth, unnumbered rule that is the whole epistemics in one line
(`checks.py:212`): *"claims support=N but cites M distinct runs — **support is
counted, not declared**."*

Levels are `reject` / `flag` / `ok`, and the verdict arithmetic is mechanical
(`checks.py:41`): any reject → `reject`, any flag → `hold`, else `admit`.
The report deep-links every citation into that run's `replay.html`.
Everything except the two LLM stages is stdlib + yaml, and
`tests/harness/test_gate.py` runs the whole chain locally with no API key.

### 6.1 The human interrupt is a file, and `apply` is the only writer

`gate review` emits `verdicts.yaml` with **two separate fields**
(`rpent/gate/report.py:110`): `suggested`, the machine's opinion, kept as an
immutable record; and `verdict`, *the human's line*, merely prefilled with the
suggestion. `gate apply` then executes strict equality — anything that is not
literally `admit` is archived into `decisions.yaml` **with its reasons**, and an
admitted proposal is still re-validated against the contract before it writes
(`rpent/gate/apply.py:110`).

"`apply` is the only writer of `memory/`" is not a convention either: **every**
sandbox profile's `write_roots` is `{output_dir}` alone, so the agent physically
cannot write under `memory/` — its proposals go to
`{output_dir}/memory_proposals/` for the gate to judge.

The four verbs encode an asymmetric evidence bar (`rpent/gate/__init__.py:19`):
*"Touching an existing entry demands more evidence than adding one — wide at the
door, strict on tenure, eviction by refutation."* In `apply.py:53`:
`support` is derived from `len(p.cited_runs)`, never from the declared field;
`provenance` is **appended**, never overwritten; and an `evict` **archives** to
`memory/evicted/` with a date stamp before unlinking, because *"an eviction is a
negative result, so it is archived, not erased."*

And the ledger gives every entry a track record read mechanically from tool
logs, with three named grounds for leaving the library
(`rpent/gate/ledger.py:1`): `refuted` (evict now), `negative` (consulted
repeatedly, runs keep failing — review), `zombie` (present for generations,
never consulted — retire). *"The ledger only reports; removal decisions go
through the same verdict flow as admissions."*

A real library entry, showing what the format buys:

```yaml
title: Grasp the butter with a shape-descriptive pi0 prompt after playbook localisation
type: technique
scope: task
conditions: after the butter is localised by the low-slab recipe; immediately
  before the pi0_pick call
support: 1
provenance:
- action: add
  evidence: [run:20260811-06:20:22_..._t6_s52#seq=32, …#seq=35, …#step=2]
- action: revise
  evidence: [run:20260811-12:50:41_..._t6_s51#seq=4, …#seq=5, …#seq=7, …#seq=14]
```

### 6.2 The generational protocol, and its honest result

Clean start (empty library) → sweep → observe/synthesize → human review →
apply → next sweep. Five generations were run. Single-run scores looked like a
growth curve, **and the curve died under repeats**:

| arm | sweeps | scores | mean |
|---|---|---|---|
| `none` (no library) | S2, S7, S9 | 4, 6, 6 | 5.33 |
| `memory` @ gen 4 | S6, S8, S10 | 5, 8, 5 | 6.0 |

≈ +0.7 out of 10 against ±1.5 per-sweep spread, n=3. Stratified: the effect is
in the middle band (t0/t1/t4/t8/t9, 9/15 vs 7/15); the easy cells don't need the
library and the hard cells it cannot save. **Report mean ± spread; never a
single sweep.** And a confound this branch's own recount surfaced: the three
`none` sweeps are not at one code head, and the 4 predates the fix for the
DeepSeek-400 orphan-`tool_calls` crash, one instance of which killed that
sweep's t5 run at 216 k input tokens where its siblings spent 4–6.6 M
([09 §4.1](09-baseline-table.md#41-the-comparisons-that-are-actually-licensed)).

What the generational protocol *did* demonstrate, and this is the claim worth
making: **the review process itself measurably improved.** Across the five
HARNESS_REVIEW cycles (`logs/gate_gen1…gen5`, local copies in
`replays/gate_reviews/`), the number of human repairs needed per cycle went
1 YAML → 4 bad paths + YAML → 1 YAML → 1 scope → **0**.

And one finding that only a ledger could produce: **reading turned selective in
gen 2** — the consultation tax died and t0/t2 recovered — but selectivity
**orphaned the anti-spiral entry**, which sat unread while t6 spiralled. That is
the data behind [issue 5e](04-open-issues.md), the one-line library index: a
need measured, not a preference.

---

## 7. Practice and exam are different regimes, enforced in code

`1197388a` · *feat(practice): experiment episodes + the task-playbook tier* ·
`ef92baad` · *the automatic debug loop*

The seed split is the protocol that keeps any of this from being cheating:
**seeds ≥ 51 are practice; seeds < 51 are scoring seeds.** Knowledge learned on
a practice seed may enter the library; a scoring seed is examined once, single
attempt, and never learned from.

It is enforced at the argument parser, not in a doc:

```python
# rpent/cli/main.py:292
if seed_num is not None and seed_num < 51:
    parser.error(
        f"--resident runs on practice seeds (>=51); seed {seed_num} "
        "is a scoring seed and a multi-attempt session there would poison it")
```

with the identical refusal for `--experiment` at `rpent/cli/main.py:382`.

**Experiment episodes** (`--experiment "<question>"`) replace the task brief with
a trials-and-conclusion brief: run up to N trials against one open question, and
write `experiment_notes.md` in relative terms. **Task playbooks** add a
`scope=task` tier to the library — per-cell technique, mined and gated exactly
like the general tier, surfaced by a prompt line that only appears when the
playbook directory both is readable and exists.

---

## 8. Resident debug sessions — the change that cracked a wall

`dd4089a3` · *feat(resident): the resident debug session* · `f9fcc18e` ·
*bounded truncation-aware nudges*

### 8.1 The argument that produced it

The owner asked for ASPIRE-style debugging (arXiv 2607.00272). The first build
was `rpent/practice`: a between-episode loop — attempt, observe, update the
playbook, attempt again. The owner pushed back twice, and was right both times:
(a) *where is the step from failure to TRYING things?* — the loop was
reflect-and-retry, Reflexion-shaped, with trying only in the escape hatch;
(b) *ASPIRE debugs WITHIN the task.* On a forced re-read of the paper:
**ASPIRE's debugger is a resident session** — one long-context session per task
that writes a program, executes it, reads curated per-primitive traces, patches,
re-executes, *all inside one continuous context that remembers every prior
attempt.* The practice loop summons an amnesiac updater per round. That
difference — continuous memory versus fresh context — is the whole mechanism.

The owner's closing insight is what made it cheap to build: **our LangGraph
turn-loop is already a live session.** In-episode, it already debugs
continuously. Three self-imposed walls blocked residency, and each got a
mechanism:

| wall | mechanism |
|---|---|
| episode boundary = session boundary | `reset_episode`, capability-gated |
| single-attempt regime (right for exams, wrong for practice) | attempt rotation into `attempt_NN/` |
| context budget (flash, not their 1M) | per-attempt folding **with a retrieval channel** |

### 8.2 `reset_episode` — existence *is* the boundary

The tool ships only under `--resident`
(`robots/libero/tools/agent_tools.py:404`, `RESIDENT_TOOLS` at `:413`), which
main.py refuses on scoring seeds and on non-deepagents planners. **An exam run
cannot be talked into a reset, because the tool is not in its surface.**
Mechanism, not prohibition — and the prompt levels to match (§3.2).

Rotation carries evidence weight, so the details are not shortcuts:

```python
# robots/libero/tools/context.py:106  (reset_episode)
#   The archive is registered write-protected: evidence of a failed
#   attempt must survive the session that produced it.
for path in (*protected_paths(self.output_dir),
             tool_log.path_for(self.output_dir)):
    if path.exists():
        path.rename(attempt_dir / path.name)
…
sandbox.add_write_protection([attempt_dir])
```

The attempt manifest records the model's own diagnosis (`reason`,
schema-enforced ≥ 20 chars): **resetting without a stated change is a rerun, not
debugging.** Per-attempt `seq` numbering restarts at 1, so `[attempt N seq M]`
is unambiguous. v1 rotation is a plain rename, and the cost of that shortcut was
measured on the very first real session — see §8.5.

### 8.3 Folding is admissible only because there is a retrieval channel

The owner's objection was that folding tool messages into digests loses
information. The resolution: it does not, **if every digest is an index entry
rather than a summary.**

```python
# rpent/planner/middleware.py:586
text = (f"[attempt {attempt} seq {record['seq']}] {name} -> "
        f"{record.get('status','?')}; {brief} | full record: "
        f"view_attempt_call(attempt={attempt}, seq={record['seq']})")
```

`view_attempt_call(attempt, seq)` (`rpent/tools/common.py:127`) resolves that key
into the one full archived record. `read_text_file` was considered and rejected
for the drill-down: it reads head-first with a char cap, so reaching call 37 of
an archived log would re-inflate the context with calls 1–36 — defeating the
fold. A line-range parameter was rejected too: paging invites re-reading whole
attempts, while a seq-addressed read returns one record by construction.

Two further properties, both deliberate:

- **Folding is a per-request view, not a state rewrite.** It happens in
  `wrap_model_call` via `request.override`; the graph state and the transcript
  keep the original messages, so the disk record stays complete and replay sees
  everything.
- **It is the first legitimate compaction in this repo.** Archives are
  immutable, so the folded prefix is byte-stable across turns and DeepSeek's
  automatic prefix cache stays warm after the first post-reset turn — unlike
  mid-list summarisation, which invalidates the cache from the edit point on
  (that trade was measured: 93% of input tokens on a real run were cache reads).

### 8.4 The result: t6, 0/11 → 3/3, with the control arm run first

**The control arm was run before the experiment, and it is reported.** The
amnesiac `rpent/practice` loop ran on t6 for 5 rounds / 115 minutes: **0 solves,
2 playbook entries, ended "no new knowledge"**. Its last two rounds ran with the
same playbook the resident session started from, which is what makes the
comparison knowledge-fair rather than a head start.

The resident session `20260811-12:50:41_libero_object_swap_t6_s51`
(454 s agent time, 74 calls, 2.4 M input) solved attempt 1 after one in-place
recovery, reset, and reproduced the solve in attempt 2 in 11 calls. The piece of
knowledge that did it is exactly the kind the amnesiac loop structurally cannot
form, because it is a **within-session contrast**:

> `pi0_pick` issued from HOME reports success and closes the fingers to **0.002**
> — an air grasp with the success flag true. The same shape-descriptive pick,
> issued after pre-positioning above the localised footprint, closes to
> **0.039** and pinches the 0.040 m slab.
> — `memory/tasks/libero_object_swap/t6/grasp_the_butter_…md`, evidence
> `run:20260811-12:50:41_…_t6_s51#seq=4,5,7,14`

Two revise proposals were mined from that run; both were HELD by the contract
check (revise requires human confirmation) and the owner approved both
(`cfb35066`).

**Exam, seed 0, playbook-armed, single attempt, no resident tools on the
surface: 3/3**, terminating at env steps 8, 15 and 7
(`20260811-13:48:21`, `-14:02:01`, `-14:18:59`); a fourth solve followed in the
next full sweep (`20260811-19:15:49`, step 2). **Cross-seed: 2/3** —
`t6_s2` solved at step 9, `t6_s3` at step 7, **`t6_s1` failed** after 21 env
steps and 120 tool calls.

**Correction to how this result has been stated.** It has been written down as
*"t6: 0/11 on seed 0 all-time"*. That is wrong as phrased, and the recount for
this PR caught it. t6 seed 0 was solved **6/7 times before the sandbox** —
including 4/4 runs that read
`resources/libero/results_object_pert/object_swap_t6_s0.json`, the answer for
that exact cell. The accurate claim is **0/11 in the clean-room era**, and it is
the stronger one: the sandbox took the answer away, the cell went dead for
eleven consecutive runs, and the harness re-derived a working recipe by
measurement. It simply has to be said that way. Full table:
[09 §5.1](09-baseline-table.md#51-t6--pick-the-butter-and-place-it-in-the-basket).

### 8.5 Two costs of this build, both recorded

- **The v1 rotation shortcut has a measured price.** The strongest refuting
  evidence for the approved grasp revision — the 0.002 air-grasp — lives in
  `attempt_01/`, and the gate's citation resolver reads only the live
  `tool_calls.jsonl`. It was **unciteable**; the proposal had to lean on attempt
  2's records. Replay has the twin problem: it renders the live layout and
  reports attempt 1's turns as record gaps. Filed as
  [issue 5c](04-open-issues.md) — the citation grammar wants an optional attempt
  segment (`run:<dir>@attempt_02#seq=N`).
- **Long sessions burn the reasoning channel.** On t5 the model spent an entire
  `max_tokens` budget inside the hidden reasoning channel and emitted an empty
  turn. `f9fcc18e` gives resident sessions up to 5 nudges after a no-tool-call
  turn and a *dedicated* message for the empty/truncated shape; **exam runs keep
  exactly one nudge, byte-identical to before**, so the exam arm's behaviour did
  not change under a fix motivated by practice.

---

## 9. The vision instrument — decoupling reasoning from perception

`63b36482` · *feat(vision): inspect_image — a VLM as a measuring instrument,
verbatim pipe* · preceded by `bdb757c6` (provider-neutral data-URI image blocks)

### 9.1 Why a tool and not a model swap

t5's wall is not knowledge and not policy: the discriminating attribute — *which
of two near-identical sauce bottles is the tomato sauce* — has **no measuring
channel**. Geometry cannot separate them; SAM3 collapses six bottle nouns onto
one xyz. The planner reasoning-spiralled trying to settle it by thought.

Vision therefore enters as a **tool**, not as a planner swap and not as a
middleware injection — the pull-shaped form that matches the project's rule that
*the planner reasons and the tools measure*:

```python
# rpent/tools/vision.py:131
def inspect_image(path, question, regions=None) -> dict:
```

The design commitments, all of them the owner's:

- **Verbatim pipe.** The reply passes through unedited — no summarising, no
  filtering, no answer extraction, no truncation. `max_tokens` is the VLM's
  generation budget, not a post-hoc cut. `_verbatim()`
  (`rpent/tools/vision.py:116`) flattens content blocks without altering words.
- **The exact text sent is recorded.** The result carries
  `sent: {system, question, crop_labels}`, so what the intermediary did is
  auditable from the run record alone.
- **The reader gets zero task context.** One fixed system line
  (`SYSTEM_LINE`, `rpent/tools/vision.py:34`) and the planner's question. *The
  reader answers about pixels; it does not know what the task is, so it cannot
  smuggle a task decision past the planner.*
- **The answer is an opinion, not a measurement.** The tool's docs entry says to
  cross-check it geometrically — the same rule as wrist readings against
  agentview anchors.
- **Regions, up to 3**, cropped from the on-disk image with a mechanical label
  (`Crop 1 = rows r0:r1, cols c0:c1 of <file>`), so a crop is a citable object.
- **Arm gating**: `inspect_image` ships only under `--vision-tool`
  (`rpent/tools/langchain_common.py:231`) — *a blind arm does not ship a tool it
  cannot honour* — and it is sandboxed like `read_image`, because otherwise it
  is a byte-exfiltration channel wearing a question mark.
- **The reader is one CLI argument.** `configure(model_spec, base_url=…)` uses
  `init_chat_model` syntax, so swapping `openai:glm-4.6v` for
  `anthropic:claude-sonnet-4-6` is the ablation, not a rewrite.

### 9.2 The thesis, and what the evidence for it actually is

The owner considers the decoupling itself the point: **reasoning runs on
`deepseek-v4-flash`; perception runs on `glm-4.6v`; neither is asked to be the
other.** The group's parallel work tests monolithic VLMs. The structural
argument is that a monolithic VLM makes the perception channel unattributable —
you cannot ask what the vision was worth, because there is no seam. Here there
is a seam, it is one CLI flag wide, and every crossing of it is a line in
`tool_calls.jsonl` with the image path attached.

**The measured evidence is thin and must be reported as thin.** Two runs, both
on t5:

- resident + vision session `20260811-20:48:01_..._t5_s51`, 201 tool calls,
  three attempts: attempt 1 failed, **attempt 2 solved at env step 13**,
  attempt 3 failed. **1 of 3 attempts.**
- exam, t5 seed 0, `--vision-tool`: `20260811-21:38:36` failed;
  **`20260811-22:05:02` solved at env step 7.** **1 of 2 runs.**

And the caveat that has to travel with them: **t5 is not a never-solved cell.**
It also fell blind twice — once pre-sandbox (`20260807-00:29:54`) and once on
the `memory` profile (`20260810-20:46:39`) — for 3/16 on seed 0 across all arms
([09 §5.2](09-baseline-table.md#52-t5--pick-the-tomato-sauce-and-place-it-in-the-basket-the-perception-channel-wall-two-visually-near-identical-sauce-bottles)).
The defensible sentence is *"the two vision-arm runs are the densest solves per
attempt we have on the cell whose wall is perceptual"*, not *"vision solved t5"*.

---

## 10. Results, and the four walls the harness can now tell apart

The most useful thing this harness produces is not a score. It is that a failure
can be **attributed to a layer**, with a citation. Four walls, four different
kinds of evidence, four different remedies:

| wall | cell | what the evidence shows | remedy that worked / is needed |
|---|---|---|---|
| **knowledge** | t6 | localisation by name fails; the recipe that works is measurable and transferable — `run:20260811-05:27:15_…_t6_s51#seq=11,12,13,24,26,29` | resident session → gated playbook entries → **3/3 exam, 2/3 cross-seed** |
| **perception channel** | t5 | the discriminating attribute has no measuring channel; SAM3 collapses six bottle nouns onto one xyz, wrong candidates scoring 0.930–0.949 *above* the target's 0.734 | a queryable vision channel (`inspect_image`); 1/3 attempts, 1/2 exams — **thin** |
| **policy** | t6 | `pi0_pick` from HOME closes to **0.002** (air grasp, success flag *true*); pre-positioned, the same prompt closes to **0.039** on a 0.040 m slab — `run:20260811-12:50:41_…_t6_s51#seq=4,5,7,14` | a discriminator the planner can *check*, since the policy cannot be retrained here |
| **environment checker** | t5 | the bottle was physically inside the basket and the flag **never fired**; an above-rim drop did fire it, and one above-rim repeat did not — `run:20260811-20:48:01_…_t5_s51#seq=41,42,74` (with `#seq=42` recorded as its own *counter*-evidence) | not fixable from here. The gated recipe tells the agent to check interior occupancy once and then **write an honest audit and stop** rather than re-place a bottle that is already in |

That last row plus `pi0_pick.success` (§5.4) is the general lesson and the reason
the scoring in [09](09-baseline-table.md) is computed from `states.json` and
never from the agent's audit: **even the environment's own flags lie**, in both
directions, and a harness that trusts them cannot measure anything.

Component error rates from the gen-0 sweep, seven completed prior-free runs,
which is where the "SAM3 is the weak link" intuition goes to die:

| component | faults / calls | rate |
|---|---|---|
| SAM3 collapse (one xyz claimed by mutually exclusive prompts) | 66/168 | **39%** |
| SAM3 no-detection (`found: false`, may be legitimate occlusion) | 61/168 | 36% |
| Pi0.5 `success=false` | 2/11 | 18% |
| `move_to` stalled (`final_dist_m > 0.02`) | 4/57 | 7% |
| harness crash (400) | 1/7 | 14% |

**SAM3 is the least reliable component and not the decisive one**: collapse rate
against solve is r = −0.10 (t3 solved at 0.52 collapse, t2 solved at 0.00, t1
failed at 0.18). The redundancy stack is doing its job, so fixing SAM3 has a
capped marginal return. The actual solve/fail discriminators are
`back_project` call count (all three solves: 0; perception-heavy failures:
54/34/12 — the fingerprint of falling back to hand-rolled geometry, which eats
the turn budget) and **two distinct exhaustion modes** — ran out *moving* (23
motions) versus never moved at all (0 motions) — which had been lumped into one
"perception loop" issue and needed different remedies.

One prompt rule turned out to be **anti-helpful** under collapse: *"two phrasings
agreeing is evidence; one high score is not."* When SAM3 collapses, two
phrasings agreeing is the same bug reported twice.

### 10.1 Bugs this project's own tooling found in this project

Listed because "the evidence layer pays for itself" is a claim, and this is the
receipt: DeepSeek-400 orphan `tool_calls` (→ `ToolCallIntegrityMiddleware`,
pre-flight repair plus a crime-scene dump of the outbound request); essay-drift
silent death (→ one nudge); post-termination crash (→ episode-over guard in
`ctx.advance`); empty-playbook advertising; a `"(none)"` placeholder being read
as a brief; program runs leaving zero evidence; `sandbox.json` recording an
empty `write_denied` because the fingerprint was dumped before the toolkit
registered protection (→ re-dump on registration).

---

## 11. What is deliberately not in this PR, and other negative results

- **The code-as-policy arm is removed** (`14b62ae2`). `rpent/cap/` implemented
  ASPIRE's Algorithm 1 faithfully — K candidates per round, Top-3 parents, debug
  on a *set* of perturbed configurations, freeze-best on budget exhaustion — and
  `--planner program` executed a frozen program with zero LLM calls in the
  episode, through the same tool handlers, so the evidence layer was identical
  across policy forms. **The plumbing was proven and the arm produced no
  result**: flash-as-coder was insufficient on t3 (8 debug runs on seed 51,
  0 solves — [09 §5](09-baseline-table.md)). It is parked on
  `refactor/langchain-native-tools`, and the replication checklist stays in
  [06-aspire-replication.md](06-aspire-replication.md).
- **A sweep pass was cut.** The `practice`-profile sweep ran one complete pass
  (7/10) and 6 of 10 cells of a second (2/6) before the owner stopped it to save
  tokens. The fragment is *worse* than the same six cells in pass 1 (4/6), so
  "7/10" is n=1 and is labelled n=1 everywhere.
- **Cross-seed transfer is 2/3, not 3/3.** `t6_s1` failed.
- **`compare_extent` does not separate success from failure**, and the
  whole-episode comparison is worthless (a 50× swing driven by camera distance).
  Both are in the tool's own documentation.
- **The staleness verdict is a lower bound**, and `pi0_pick`'s descent is
  invisible to it.
- **Two objects with exchanged labels are geometrically indistinguishable** and
  the databus says so rather than guessing.
- **Four middleware in the declared order are not implemented**
  (`InjectionLedgerMiddleware`, `GateMiddleware`, `ProvenanceMiddleware`,
  `CompactionMiddleware` for exams).
- **`--interactive` raises `NotImplementedError`** on the deepagents planner
  rather than being silently ignored, because silently ignoring it would let
  someone believe they were steering a run they were not.

---

## 12. Positioning: the harness is grown, not adopted

The reviewer's first question is *"why not just use deepagents, or Claude Code's
harness?"* Because desktop-agent harnesses encode four assumptions that
embodiment breaks:

1. **Actions are reversible and cheap**, so they optimise throughput —
   parallelism, speculative work, subagent fan-out. Embodiment demands
   evidence-before-commitment: the advancing/read-only split, staleness
   verdicts, post-action verification.
2. **The world is text**, hence their virtual filesystem. Here, heavy data lives
   on disk and citations live in context; text is only a *projection through
   measurement*.
3. **A cheap oracle exists** ("run the tests"). Embodiment must *build* its
   judge — and even the environment's own flags lie (`pi0_pick.success`, §5.4).
4. **Tasks decompose into independent contexts.** An episode is one continuous
   world and one body. Only read-only perception over dumped artifacts may
   fan out.

LangGraph is the shared chassis. The harness is grown twice over: **hand-grown**
from embodied constraint crossed with three project rules — *mechanism over
discipline*, *attribution*, *measure don't recall* — and **self-growing** through
the gate, with the growth itself measured (repeats, ledger, review-quality
line). That double meaning is the position.

Nearest neighbours, read and cited rather than ignored:

- **ASPIRE** (arXiv 2607.00272) has the resident-session mechanism and the
  per-primitive trace engine — their ablation of that engine is the paper's
  largest effect, 14% → 62% macro-average, with evolutionary search adding only
  62% → 72%. *The evidence layer is the main course; search is dessert.* What
  they do not have is our measurement of the growth itself.
- **Thea** is the same species on real robots — Scene Graph as Context,
  Evaluation as Exit Codes with forced post-hooks, 93.3% evaluator accuracy —
  but its `update_memory` writes freely and it measures no generations. Our
  niche is measured, gated, clean-room growth.
- **OpenETA** (arXiv 2608.03924) is ahead of us in three named places and this
  is recorded rather than buried: their evidence-boundary trichotomy (tool
  completion / world-state change / task success — now quoted in
  `compare_extent`'s contract), `select_sam3_detection` as a *forced* obligation
  when segmentation is ambiguous (ours silently returns the top mask — a real
  gap), and the fresh-observation obligation as a *gate* rather than a report.
  Where we fork: they outsource "where to grasp" to learned predictors; we have
  the planner reason over measured constraints from a frozen VLA's primitives.

---

## 13. How to check any of this

```bash
# the whole regression suite, no API key, no GPU
for t in deep_agent resident vision_tool tool_docs prompt_leveling \
         sandbox databus shape gate practice replay locateanything; do
  PYTHONPATH=. python tests/harness/test_$t.py
done

# did a run consume a prior?  (should be empty for every sandboxed run)
grep 'read_text_file' run.log | grep -E 'results_.*_pert|env_calibration'

# rebuild any run's evidence from disk alone
PYTHONPATH=. python -m rpent.replay <run_dir>
```

`test_deep_agent.py` drives the real planner, middleware, tools and context
against a scripted chat model; `test_resident.py` drives a scripted two-attempt
session end-to-end including the fold and the drill-down. If those pass, the
wiring is intact.
