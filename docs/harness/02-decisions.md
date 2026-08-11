# Decisions, and why

Each entry is a decision that is not obvious from the code, with the argument that
settled it. Where a decision was reversed, both directions are recorded — a future
session that re-derives the discarded option will waste a day.

## Tool layer

### Native LangChain tools, and the schema-authoring reversal

The first adapter passed the toolkit's existing JSON Schema dicts straight into
`StructuredTool(args_schema=<dict>)`, which LangChain accepts and passes through
byte-identically. That was chosen so the schema the model sees could be *proven*
unchanged across the migration — the whole surface hashed to `c646df3d…` before and
after.

**Then reversed on the owner's call**: schemas are now authored as Pydantic models. The
argument for the reversal is sound — one definition gives validation, the schema, and
IDE types, and it scales as tools are added. Cost accepted: the rendered JSON Schema
shape differs (`anyOf`, `title`, `default`), so that hash is void.

**Trap that cost real time**: Pydantic `list[float]` needs explicit
`min_length`/`max_length` to emit `minItems`/`maxItems`. Without them the array-length
constraint silently disappears.

### `agent_tools.py` must NOT use `from __future__ import annotations`

LangChain detects the `ToolRuntime` parameter by resolving the annotation to the real
type. Under PEP 563 it sees the *string* `"ToolRuntime"`, detection silently fails, and
every call dies at dispatch with `missing 1 required positional argument: 'runtime'` —
**at dispatch, not at import**. Verified against langchain-core 1.5.3 / langgraph
1.2.10 with a minimal two-file reproduction.

### Module-qualified imports in `agent_tools.py` (`perception.back_project(...)`)

Not style. `@tool` takes the tool name from the function name, so the tool function must
be named `back_project` — and so is its handler. A name import would be shadowed by the
`def`, and after decoration the module global is a `StructuredTool`, so the body would
call a non-callable (`TypeError: 'StructuredTool' object is not callable`). Three of 14
tools collide this way: `view_driver_state`, `view_camera_meta`, `back_project`.

### Live handles reach tools via `ToolRuntime`, not a closure or a global

`LiberoContext` is passed as the graph's `context` and read as `runtime.context`. A
module global would break parallel runs in one process; closures would stop the tools
being module-level and greppable. Verified that `context_schema=LiberoContext` +
`invoke(..., context=ctx)` passes through `create_agent`'s internally-built graph — this
was the single biggest unknown before the planner was written.

The three read-only tools that need no live handle (`view_driver_state`,
`view_camera_meta`, `back_project`) deliberately omit the parameter, so they stay
callable outside a graph, which offline diagnostics rely on.

### Keeping `agent_tools.py` separate rather than `@tool` in each kind file

Considered and rejected. 9 of 14 tools wrap **mixin methods** (`MotionMixin.move_to`
etc.), and `@tool` cannot decorate a method — `self` would become a tool argument.
Collapsing them would require renaming every physics function so the tool could own the
good name (`move_to` → `_servo_position`), which is a worse name forced by a framework
constraint. Two namespaces let both layers keep the correct name. Net saving would have
been exactly one file.

## Planner

### `create_agent`, not `create_deep_agent`

`create_deep_agent` is the same graph plus subagents, skills, memory, permissions and a
virtual filesystem — and it injects its own system prompt and tools. Those are real
capabilities but they are *additional injections*, and an injection that is not declared
cannot be accounted for. They ship as individual middleware (`SubAgentMiddleware`,
`FilesystemMiddleware`, `MemoryMiddleware`, `RubricMiddleware`), so each can be added
later as a named, toggleable entry and measured on its own. Starting here keeps the
injected surface equal to the system prompt plus the declared tools.

### Turn budget via `ModelCallLimitMiddleware`, not `recursion_limit`

`recursion_limit` counts graph nodes, not model turns, and the cost per turn grows with
the middleware chain. Measured on langgraph 1.2.10: the minimum viable limit is
`(3 + len(middleware)) * turns + 2` — slope 4 with one middleware, 5 with two, linear
after. A hardcoded multiplier produced a spurious `GraphRecursionError` at
`max_turns=5`. It is now derived from the middleware count with a 2x margin and serves
only as a backstop against a graph that loops without calling the model.

### Chat model built in `build_planner`, not in `solve`

An unusable `--model` used to raise only once `solve` ran — after
`env_spec.init_runtime` had spent minutes loading Pi0.5 and SAM 3.0 onto the GPU. Two
limits remain and match the pydantic-ai planner: a missing API key still surfaces at the
first request, and `init_chat_model` accepts a bare model id by inferring the provider.

### `finish` stays a tool

`create_agent` ends when the model stops calling tools, so `finish` is not structurally
necessary. Kept so `PlannerResult.finish_result` stays comparable across planners and
the audit flow is unchanged.

### `--interactive` raises `NotImplementedError`

LangGraph steers through human-in-the-loop interrupts, not a mid-run message queue, so
it is separate work. Raising is deliberate: silently ignoring the flag would let someone
believe they were steering a run they were not.

### One toolkit object serves both substrates

`LiberoToolkit` gained `langchain_tools()` and `tool_context` rather than a parallel
session object. Result: the `Planner` protocol unchanged, the runner's lifecycle
(`close()`, `write_recipe()`) unchanged, and `main.py` needed a single line. Cost:
`_step` and `advance` both exist during the migration; only one runs per run, and the
duplication disappears with the legacy path.

### `tool_calls.jsonl` is separate from `states.json`

`states.json` entries are keyed by env step, and read-only calls happen *between*
steps. Merging them would break the `step_idx` contract that `view_driver_state`,
`_load_step` and the recipe exporter depend on.

Written from `wrap_tool_call` because that is the only seam that sees every call
uniformly — including `read_text_file`, which matters most given the prior-leak problem.
A separate middleware from `TranscriptMiddleware` because the audiences differ
(diagnostics vs planner output) and because it must be toggleable on its own: it is the
input to any after-the-fact attribution.

## DeepSeek

### `--model deepseek-v4-flash` needed no code change

`init_chat_model` routes any `deepseek*` id to `langchain_deepseek.ChatDeepSeek`, with
or without the provider prefix, and the existing `--base-url` passthrough lands on
`ChatDeepSeek.api_base` (`base_url` is its alias). `DEEPSEEK_API_KEY`; default base
`https://api.deepseek.com/v1`. A `beta` base exists for strict schema validation if
tool arguments ever drift.

### Cache accounting needed a provider-native fallback

DeepSeek's context cache is **automatic server-side prefix caching** — nothing to enable
client-side, unlike Anthropic's `cache_control`. But it reports the outcome as
`prompt_cache_hit_tokens` / `prompt_cache_miss_tokens`, and no adapter maps those into
`usage_metadata.input_token_details`. Reading only the standardised field would have
shown zero cache hits on every DeepSeek run while the cache was working — **silently
reading zero is worse than reading nothing**, because the ledger then claims the cache
never helped. Confirmed on a real run: 93% hit rate, `cache_write=0` as expected.

### The entity index rides in tool results, not in an injection

"Put it in graph state" does not make it visible: LangGraph state fields other than
`messages` are invisible to the model, so visibility needs an injection either way.
Injecting into the system message would rewrite byte 0 every turn and miss the automatic
prefix cache entirely. Appended tool results leave the prefix byte-stable and surface the
index exactly when the planner is looking at state.

**Corollary for compaction**: `SummarizationMiddleware` / `ContextEditingMiddleware`
rewrite the middle of the message list, invalidating the cache from that point on. Their
token saving is partly offset, and that trade must be measured, not assumed.

## Databus

### Append-only readings, never a mutable "current position"

A mutable current value destroys the provenance `world_path` exists to provide — a motion
could no longer cite the reading it was planned from. It also forecloses fusion:
combining viewpoints is a *computation over readings* that yields another reading.
Averaging is deliberately not offered: two readings of a container's near wall have
biases that may cancel, but two readings that caught an object's body and its cap average
to a point on neither. A reducer has to know what it reduces, so reduction stays an
explicit tool.

### Staleness is computed by the harness, interpreted by the planner

Verdicts: `fresh`, `unverified` (world changed, arm stayed away — *not known to be
disturbed*, not *known untouched*), `possibly_bumped`, `held`. **Documented
approximation**: only the eef poses before and after an action are available, so
proximity is tested against the straight segment between them. `pi0_pick` descends and
lifts back to nearly the same point, so its descent is invisible to that test. The
verdict is a lower bound on disturbance.

### Conflicts are reported, never resolved

`identity_warning` (same entity, distant new reading) and `collision_warning` (two
different names within 3 cm) both surface a tension the harness cannot settle — only the
planner knows whether an object was supposed to have moved. The collision radius comes
from data: real tabletop objects sat 6-20 cm apart while one object's repeated readings
agreed to millimetres.

**Stated limit**: two objects at two distinct places with their labels *exchanged* are
geometrically self-consistent and no measurement separates them. The only resolution is
an independently-phrased query — ask for a discriminating attribute rather than the name
and check it lands on the same reading. Two phrasings agreeing is evidence; one high
score is not.

## Geometry tools

### `shape` reports object geometry, never a `target_yaw`

Which eef axis the fingers close along is gripper geometry. A wrong 90 degrees there
would rotate every grasp orthogonal to correct while looking entirely reasonable, and
silently. So the tool reports `graspable_width_m` (the span the fingers must cover) and
`short_axis_yaw_deg` (the direction they travel), and states that the mapping onto
`rotate_wrist` is a one-time measurement. Being a hardware invariant rather than a
per-seed number, that mapping is exactly what memory should hold.

Yaw is an **axis**, not a direction: an eigenvector's sign is arbitrary, so it is folded
into [-90, 90) and a grasp is equally valid either way along it.

### Shape ratios from standard deviations, extents from min-max

A square footprint's fitted axes land on its diagonals, so its min-max range overstates
the side by up to sqrt(2) — enough that a 0.09 m cube classified as "lying". A square's
covariance is isotropic whatever its rotation, which is the invariance the ratio tests
need. Min-max is still what gets *reported*, because a gripper has to span the full
width, not one sigma.

### `compare_extent` compares adjacent steps

Over a whole episode the point count inside one fixed box swung 50x purely because the
wrist camera ended up closer, so voxel counts tracked how much the cameras saw rather
than what was there. Adjacent steps share a viewpoint. See `03-findings.md` for the
numbers, and for why a change here is still not task success.

## Prompt cleansing

### The admission rule is two-dimensional, and "contains a number" is not it

That filter is wrong in both directions. A drawer's In-region bounds are numeric,
invariant, and not perceptually recoverable — that is knowledge. "The dark bottle is the
salad dressing" has no numbers and is pure answer.

|  | varies with the instance | invariant |
|---|---|---|
| **a tool can measure it** | never in the prompt — measure it | at most a check, never a value |
| **no tool can recover it** | this is the cheat (a cell's answer) | **the only class worth its tokens** |

What survived: frame conventions (`+y = robot-LEFT`), gripper semantics, which primitive
threads an IK singularity, the wrist camera's modality weakness, and a stalled `move_to`
being a failure at `final_dist_m > 0.02`.

What was deleted: the per-task `t0`-`t9` recipe blocks and all their coordinates;
`KEY_HYPERPARAMETERS` (per-object thresholds duplicating tool schema defaults, plus
scene-specific eef heights); `eef_y = plate_y + 0.045` (measurement refuted it);
WORKFLOW step 3 "read the seed-0 reference" — the leak channel itself.

### `env_calibration.md` is no longer injected

187 numeric constants, with sections titled "OSC reachable workspace" and
"Object-level reference heights" — a probe log turned into a lookup table, including "Use
z=0.53 for basket releases" derived from one scene and `libero_10_with_mug t0` named
directly. The object heights are now `segment().shape.height_m`.

### Prompt and tool description divide cleanly

The prompt says **when and why** (procedure, regime, non-recoverable invariants); the
tool description says **what and with which caveats**. Before, `|Δxy| > 0.30` appeared in
both. Now the tool description owns it.

## Sandbox

### `--sandbox <profile>`, not `--priors {none,memory,full}` — an owner reversal

The handoff recorded `--priors` as the decided shape. The owner reversed the
naming on 2026-08-07: the flag selects a *sandbox profile*, and calling it that
makes the mechanism legible to a reader who has not seen the experiment design.
The three arms keep their names — as profile *files*, not as an enum. Code never
special-cases a profile name; `configs/sandbox/<name>.yaml` is the whole story,
and a custom path can be passed for one-off arms.

### The sandbox is always on; permissiveness is a declared profile

There is no `--sandbox off`. Debugging without a boundary is
`configs/sandbox/unrestricted.yaml` — a fingerprinted state whose runs
self-identify as measuring nothing. Until `set_sandbox()` runs, every check
fails closed. Rationale: a leak must not be reachable by forgetting a flag.

### Profile = shape, env = binding

Profiles reference placeholders (`{output_dir}`, `{memory_common}`,
`{memory_env}`, `{staging_root}`, `{repo_root}`); `default_bindings()` resolves
them per run from `--env`. One `memory.yaml` therefore serves libero, robocasa,
and whatever comes next, and "the memory arm" stays the same experimental
condition across environments. Per-env profile copies were considered and
rejected: they drift, and they silently fork the arm's meaning.

### Config declares intent; code owns invariants

`write_denied` — the harness-owned evidence inside the output dir
(`states.json`, `tool_calls.jsonl`, the world/image dumps, `sandbox.json`
itself) — is registered from `ARTIFACT_LAYOUT` by the toolkit
(`artifacts.protected_paths`), never loaded from a profile. An agent that can
rewrite its own evidence log invalidates every attribution claim, so that
boundary is not configuration. Writes are `{output_dir}`-only in every shipped
profile, including `unrestricted`; the memory library is reachable only through
the promotion gate (agent proposals go to `{output_dir}/memory_proposals/`).

### `read_image` is sandboxed too

Without the check it is a generic byte-exfiltration channel (any file, base64,
straight to the model), not an image viewer.

### The sync is opt-in and staged

`ensure_staged_priors` replaces `ensure_resources`: nothing downloads unless
the active profile references `{staging_root}` (only `full.yaml` does), the
target is `.staging/<env>/` rather than `resources/`, an existing staging copy
is reused, and a partial sync raises instead of warning — a comparison arm on a
silently partial payload measures nothing. The decoupled library under
`memory/` is never a sync target.

### The prompt levels on capabilities, not profile names

`system_prompt(memory=...)` / `user_prompt(memory=...)` take a boolean that
main.py reads off the LIVE policy (`sandbox.memory_exposed`), never the
profile's name. A custom profile that exposes the library roots gets the
library instructions automatically; one that does not gets a prompt in which
the library was never mentioned. Consequences that were deliberate:

- **Every verbal file prohibition was deleted**, in every variant. The ⛔
  blocks ("do NOT read `results_*`", "do NOT read `env_calibration.md`") were
  discipline standing in for a missing mechanism; with the sandbox they became
  pure advertisement — naming a blocked file tells the model it exists and
  what it contains. The prior-free prompt now reads as if those files never
  existed, which is the test (`test_prompt_leveling.py`) not a metaphor.
- The guides step is gone from all variants: no shipped profile exposes
  `robots/libero/guides/`. If the guides are later seeded into the memory
  library, the generic "scan the library roots" step picks them up with no
  prompt change — prompt and library contents are decoupled.
- `EVIDENCE_DISCIPLINE` keeps "measure, do not recall" (positive epistemics,
  true in every arm) but no longer names `resources/`; the technique-not-values
  rule moved into the memory step, its single owner.

### Known limit

The `claude_code` / `codex` planners are external CLI agents with their own
filesystem access; the sandbox governs the in-process tool layer only. They
also still receive the legacy `resources/<env>/memory` path via
`get_memory_dir` — untouched, per the standing decision not to modify those
planners.

## Resident debug sessions (2026-08-11)

### Folding is admissible only with a retrieval channel

The owner's concern, verbatim in spirit: folding tool messages into digests
loses information. The resolution: it does not, IF every digest is an index
entry rather than a summary. Each folded tool result becomes one line
carrying its citation key `[attempt N seq M]`, and `view_attempt_call`
resolves that key into the full archived record — one call, one record. This
mirrors ASPIRE's evidence engine (the resident agent pulls per-call evidence
by index) and reuses the `#seq=N` citation format the gate and replay
already speak. `read_text_file` was considered and rejected for the
drill-down: it reads head-first with a char cap, so reaching call 37 of an
archived log would re-inflate the context with calls 1-36 — defeating the
fold. A line-range parameter was rejected too: paging invites re-reading
whole attempts; a seq-addressed read returns one record by construction.

### Folding is a per-request view, not a state rewrite

`AttemptFoldingMiddleware` folds in `wrap_model_call` via
`request.override`; the graph state and the transcript keep the original
messages, so the disk record stays complete and replay sees everything.
Corollary that makes this the first legitimate compaction: archives are
immutable, so the folded prefix is byte-stable across turns and the
provider's automatic prefix cache stays warm after the first post-reset
turn — unlike mid-list summarisation (see the DeepSeek cache section).

### The join is by call_id, not by position

`tool_calls.jsonl` records gain a `call_id` field (the provider's tool-call
id, written by `ToolCallLogMiddleware`). Position-based alignment between
the message list and the log was rejected: parallel calls in one turn can
land in the log in a different order than in the message list, and a
misattributed seq in a digest is worse than none.

### Tool existence is the regime boundary

`reset_episode` and `view_attempt_call` ship only under `--resident`
(read_image-variant pattern), which main.py refuses on scoring seeds
(< 51) and on non-deepagents planners. An exam run cannot be talked into a
reset because the tool is not in its surface — mechanism, not prohibition.
The prompt levels the same way: the resident regime REPLACES the
single-attempt blocks (⛔ FORBIDDEN: `reset` etc.), because a prompt that
forbids resetting while the tool list ships `reset_episode` advertises a
false boundary. `test_prompt_leveling.py` asserts both directions.

### Rotation details that carry evidence weight

Per-attempt seq numbering restarts at 1 (the reset call itself lands as
seq 1 of the new attempt's log), so `[attempt N seq M]` is unambiguous.
The archive (`attempt_NN/`) is registered write-protected the moment it is
created — evidence of a failed attempt must survive the session that
produced it. The attempt manifest records the model's own diagnosis
(`reason`, schema-enforced >= 20 chars): resetting without a stated change
is a rerun, not debugging. v1 rotation is a plain rename; replay and gate
read the live layout and see only the newest attempt (accepted shortcut,
refine when the resident sessions earn it).

## Comparison with OpenETA

OpenMOSS/OpenETA (arXiv 2608.03924) covers much of the same governance ground. Read it
before claiming novelty. Where it is ahead and worth adopting:

- **Evidence-boundary trichotomy**: tool completion, world-state change and task success
  are three distinct claims. This framing is sharper than anything we had and is now
  quoted in `compare_extent`'s contract.
- **`select_sam3_detection` as a forced obligation**: when segmentation returns multiple
  candidates, their runtime inserts an explicit selection step and gates grasp planning
  until it happens. Our `segment` returns only the top-ranked mask, so multi-candidate
  ambiguity is silently collapsed — a real remaining gap.
- **Fresh-observation obligation as a gate**, not a prompt instruction: every
  world-mutating action creates an obligation to re-observe. That is the mechanism form
  of what our staleness verdicts currently only report.
- **Host-computed promotion gates**: agent-supplied percentages are not accepted as
  promotion evidence; the host reads the artifacts and computes the numbers.

Where we differ by design: their manipulation stack outsources "where to grasp" to
learned predictors (AnyGrasp/GraspGenX/AnyPlace) plus promoted grasp strategies, and
their policy adapters are unadapted. Ours has the planner reason over measured
constraints from a frozen VLA's primitives. That is the actual research fork, and it is
where this repo's contribution has to live.
