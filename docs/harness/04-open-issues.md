# Open issues, in priority order

## 1. Stop the HuggingFace sync; make the prior level a configuration

**IMPLEMENTED** as `--sandbox <profile>` (profiles in `configs/sandbox/`,
enforcement in `rpent/tools/sandbox.py` + `rpent/tools/common.py`, tests in
`tests/harness/test_sandbox.py`). The owner renamed the flag from the
`--priors` shape recorded below; see the Sandbox section of
[02-decisions.md](02-decisions.md) for the full decision record. The prompt
channel is leveled in a separate commit (so the two injection channels stay
individually attributable): the prompt varies with the sandbox's
*capabilities* (`memory_exposed`), the library step exists only when the
library is readable, and every verbal file prohibition is gone — a file the
sandbox blocks is not mentioned at all, because naming it to forbid it
advertises it. Lint: `tests/harness/test_prompt_leveling.py`. The original
issue text follows for context.

`ensure_resources` (`rpent/utils/resources.py`) pulls `RLinf/RPent-memory` into
`resources/libero/` on **every run**, with `local_dir` set so it **overwrites what is
there**. What lives on HF is the magic-numbers-and-priors payload, which makes the
sync the delivery mechanism for exactly what the prompt cleansing removed:

- deleting the priors locally does not stick — the next run reinstalls them;
- any locally curated memory is clobbered;
- pre-existing `results_*` may already have been overwritten by a pull;
- one run's sync died with `429 Too Many Requests` and the exception was swallowed,
  leaving `resources/` **partially** updated with no signal beyond a warning.

The intended shape, which the owner described as "put the robot in a clean
environment each run":

```
--priors {none, memory, full}
```

| level | what `read_text_file` can reach |
|---|---|
| `none` | `{output_dir}` only |
| `memory` | + `resources/libero/memory/`, `guides/strict_hybrid_guide.md`, `guides/pro_hybrid_guide.md` |
| `full` | + `results_*_pert/` — kept only as a comparison arm |

Two pieces:

1. **A readable-root allowlist in `rpent/tools/common.py`.** `_resolve` currently
   does `get_repo_root() / path` with **no sandbox**, which is why `Rule 2b` ("never
   read the BDDL") has always been prompt-enforced rather than harness-enforced. One
   allowlist turns three standing prohibitions into mechanism.
2. **Sync off by default**, or at minimum never overwriting; if a sync is wanted,
   fetch to a staging path and let the level decide what is exposed.

Side benefit measured on a real run: 41% of tool calls were file reading. At `none`
or `memory` that shrinks, saving turns and input tokens.

Note `feedback_bowl_eef_y_offset.md` still lives in the memory library and holds the
`+0.045` constant that measurement refuted. Cleansing the prompt did not clean the
library.

## 2. Two sweep runs never issued a motion command

`t2` and `t3` in the prior-free sweep spent their whole turn budget on perception:

```
t2: 6 turns / 22 calls — segment x14, motion x0, finish=null
t3: 9 turns / 37 calls — segment x24 + world_extent x4, motion x0, finish=null
```

Plausibly a side effect of the cleansing: the new prompt mandates "localize
everything, register every entity, pass the READY CHECK before acting", and without a
per-cell recipe to anchor on it may not converge. Candidate remedies, in increasing
intrusiveness:

- Give the READY CHECK a **budget**: after N perception calls without a motion,
  instruct it to commit to its best current estimate and say so in the audit.
- Cap `segment` calls per entity (`ToolCallLimitMiddleware` is prebuilt).
- Have the entity index report how many perception calls have happened, so the agent
  can see its own loop.

Do not fix this blind — read both transcripts first. The distinction that matters is
whether it was *stuck* (re-segmenting the same thing) or *lost* (couldn't ground the
noun at all); the two need different remedies.

## 3. `pi0_pick`'s success predicate penalises good pre-positioning

`descent >= 0.10` is false whenever the agent pre-positions close, which the prompt
teaches it to do. On the one run examined, `success=false` on a grasp that worked.
The prompt now says to ignore the flag, which is discipline. The mechanism fix is to
drop `descent_done` from `success` and leave it in `diagnostics`, or to make the
threshold relative to the object's top surface (now measurable via
`segment().shape`).

## 4. Context growth vs the prefix cache

Context went 17.7k → 79.9k over 17 turns (~3.9k of tool results per turn). Fine at 17
turns, untenable at `--max-turns 100`. But compaction rewrites the middle of the
message list, which **invalidates DeepSeek's automatic prefix cache from that point
on** — and 93% of input tokens were cache reads. The trade must be computed, not
assumed. The data to compute it is in the run logs.

## 5. `GateMiddleware`, in shadow mode first

`wrap_tool_call` sees `tool_call` / `tool` / `state` / `runtime`, so a gate can reject
before the environment moves. Candidates with measured backing:

- `move_to` with `|Δxy| > 0.30` (already in the tool description as advice)
- an advancing tool whose target entity has no `fresh` reading
- a grasp while an `identity_warning` or `collision_warning` is unresolved

**Run every gate in shadow mode first** — evaluate, log "this would have been
blocked", do not block. That gives the trigger rate and the false-positive rate before
anything is enforced, and it also produces the matched-pair data that makes a later
A/B interpretable.

## 5b. Gen-0 sweep findings (2026-08-07, t0-t6 completed at time of analysis)

Measured per-component error rates, seven completed prior-free runs:

| component | faults/calls | rate |
|---|---|---|
| SAM3 collapse (one xyz claimed by mutually exclusive prompts) | 66/168 | **39%** |
| SAM3 no-detection (`found: false` — may be legitimate occlusion) | 61/168 | 36% |
| Pi0.5 `success=false` | 2/11 | 18% |
| `move_to` stalled (`final_dist_m > 0.02`) | 4/57 | 7% |
| harness crash (400) | 1/7 | 14% |

Three conclusions that survive the numbers:

1. **SAM3 is the least reliable component but not the decisive one** —
   collapse rate vs solve is r = −0.10 (t3 solved at 0.52 collapse, t2 solved
   at 0.00, t1 failed at 0.18). The redundancy stack (collision_warning,
   independent phrasing, back_project fallback) is doing its job, so fixing
   SAM3 has a capped marginal return.
2. **The real solve/fail discriminators**: `back_project` call count (all
   three solves: 0; perception-heavy failures: 54/34/12 — the fingerprint of
   falling back to hand-rolled geometry, which eats the turn budget), and two
   DISTINCT exhaustion modes (t4: 23 motions, ran out moving; t5-class: 0
   motions, never moved). Lumping both into "issue 2 perception loop"
   misdiagnoses.
3. **One prompt rule is anti-helpful under collapse**: "Two phrasings
   agreeing is evidence; one high score is not." When SAM3 collapses, two
   phrasings agreeing is the same bug reported twice (t5: six bottle nouns on
   one xyz, wrong candidates scoring 0.930-0.949 ABOVE the target's 0.734).
   The mechanism form: the databus already computes "N mutually exclusive
   prompts on one xyz" — promote it from a warning to a rejection condition
   (a GateMiddleware candidate, shadow mode first per issue 5), and fix the
   prompt sentence in the same changepoint.

**Resolved from the same sweep**: the t5 400
(`insufficient tool messages following tool_calls` after a 16-parallel-call
turn; transcript held a paired 50/50 record, so the corruption was in the
outbound request nobody dumped) → `ToolCallIntegrityMiddleware` now repairs
orphan tool_calls pre-flight and dumps the outbound request on provider
rejection. Root cause still open; the next occurrence will carry a full
crime scene. Also fixed: `sandbox.json` recorded an empty `write_denied`
(fingerprint dumped before the toolkit registered protection) — the
fingerprint now re-dumps when protection registers.

## 5c. Gate citations and replay cannot see archived attempts

Surfaced on the first real resident session (2026-08-11, the t6 crack):
the v1 rotation renames an attempt's evidence into `attempt_NN/`, but

- the gate's citation resolver only reads the live `tool_calls.jsonl`, so
  a proposal cannot cite the failure it fixes when that failure lives in
  an archived attempt (the 0.002 air-grasp — the decisive refuting
  evidence for the approved grasp revision — was unciteable; the
  proposal had to lean on attempt 2's summary records);
- replay renders the live layout only, so the resident run's replay
  shows 14 calls of attempt 2 and reports the transcript's attempt-1
  turns as record gaps.

The citation grammar wants an optional attempt segment
(`run:<dir>@attempt_02#seq=N` or similar), resolved into
`attempt_NN/tool_calls.jsonl`; replay wants an attempt picker (or
per-attempt pages). Accepted as v1 debt when the rotation shortcut was
approved; this run converted it from hypothetical to measured.

## 5d. The vision triangle: `inspect_image` tool + three-arm modality ablation

Agreed with the owner 2026-08-11 evening, motivated by the t5 wall (the
discriminating attribute — which sauce bottle is which — has no measuring
channel, and the planner reasoning-spiraled trying to settle it by thought).

Design: vision enters as a TOOL, not a planner swap and not a middleware
injection — the pull-shaped form that matches "planner reasons, tools
measure". `inspect_image(path, question, region?)` sends one image (optionally
cropped to a segment bbox) to a cheap VLM (glm-4.6v via InfiniAI) and returns
its textual answer; sandboxed like read_image; every call lands in
tool_calls.jsonl with the image path as evidence. The tool's answer is an
OPINION, not a measurement — its docs entry must say to cross-check
geometrically, same rule as wrist readings vs agentview anchors.

The ablation arms (each a fingerprinted configuration):
1. flash blind (baseline — all existing data);
2. flash + inspect_image (`--vision-tool`): what a QUERYABLE vision channel
   is worth. **IMPLEMENTED** (`rpent/tools/vision.py`, verbatim-pipe
   contract per the owner: the reply passes through unedited, the exact
   text sent is recorded, the reader gets zero task context;
   `tests/harness/test_vision_tool.py`).
3. full VLM swap: CANCELLED as a routine arm by the owner (experiment time
   / cost); kept as an OPTIONAL strong-model comparison (sonnet / gemini
   via the same `--model` + `--base-url` route, verified working) for when
   the modality question deserves the spend.

Relation to the perception overhaul (5b/认东西链大修): complementary, not
competing — inspect_image gives fast semantic discrimination (opinion-grade),
LocateAnything + colour/size stats give auditable numbers (measurement-grade).
Build order: inspect_image first (hours), overhaul after Friday.

## 5e. The one-line library index, with `conditions` as its key and
## `requires` as its filter

Agreed with the owner 2026-08-11 evening. Every entry already carries a
prose `conditions:` line ("when it applies") — kept PROSE by explicit owner
decision: structure only what a mechanism actually consumes, and today
that is exactly one thing. The package:

- entries gain an OPTIONAL structured `requires: [tool names]` field
  (arm-dependent knowledge, e.g. a recipe that leans on `inspect_image`);
- the long-queued one-line index is generated PER RUN by the harness:
  one line per entry = name + conditions + one-line what;
- the generator consumes `requires` against the run's actual tool
  surface: an entry whose requirement is absent does not appear in that
  run's index — the library-side twin of prompt capability leveling
  ("a technique the surface cannot honour is not advertised");
- later, the ledger can audit consumption QUALITY against conditions
  (entry consumed outside its stated conditions + run failed = a revise/
  evict signal), and structured preconditions are the long-run bridge
  between text memory and the CaP program library.

**URGENT as of 2026-08-14** (promoted from queued). The gen-0 distillation
admitted 37 new entries in one batch, roughly doubling the common tier. A
library that a run must scan in full is a library whose consultation cost grows
with every generation, and the ledger has already measured the failure mode
once: selective reading in generation 2 recovered two cells and simultaneously
orphaned an entry that then sat unread while the cell it addressed spiralled.
At the new size that trade stops being a curiosity. The one-line index, filtered
by the run's actual tool surface, is now the blocking dependency for further
growth rather than a nicety.

The index need itself is data-backed: gen2's selective reading orphaned the
anti-spiral entry while t6 spiraled.

**UPDATE 2026-08-12 — the predicted exposure has now been observed.** Both
blind t5 runs in the practice-arm sweeps (`20260812-00:53:35`,
`20260812-03:15:06`) read **all five** t5 playbook entries at seq 5–9 with
**`inspect_image` call count 0** — the tool is absent on a blind arm. One of
those entries, the owner-edited
`localize_extra_bottle_clusters_geometrically_not_by_color_la.md`, instructs
the agent to *"`back_project` the pixel and require the returned z to sit near
table level"* — a procedure that presupposes a VLM pixel the arm cannot
obtain. Both runs failed.

**No causal claim**: the transcripts have not been read, so whether the
unexecutable entries cost anything is unknown. What is established is that
the exposure scenario `requires:` was specified to prevent **occurs in
practice**, which moves the motivation from anticipated to empirical. The
impact is unquantified and should be stated that way until someone reads the
two transcripts.

## 5f. A gated entry became an excuse (found 2026-08-12)

The sharpest negative result the vision sweep produced, and it is about our own
mechanism rather than the model's.

`memory/tasks/libero_object_swap/t5/release_from_above_the_rim_do_not_descend_into_the_basket.md`
says, correctly and with resolving citations, that this cell's checker is flaky:
after an above-rim release, verify interior occupancy once, and if the flag has
not fired, **write the honest audit and stop** rather than re-place a bottle
that is already in the basket. It was admitted through the gate properly — its
numbers trace, its cites resolve, and its `counter_evidence` even declares the
repeat that failed to fire.

Both t5 failures in the vision sweep (`20260812-12:06:23`, `20260812-14:15:31`)
picked the **wrong object** — the BBQ bottle at `[-0.19,-0.07]`, over the
instrument's own correct "brown / BBQ sauce" reads — placed it in the basket,
and then cited this entry to explain the non-firing checker. The checker was
right. The entry gave a wrong-object run a ready-made, honest-sounding reason to
stop looking, and both runs took it and wrote confident audits
([09 §4.1e](09-baseline-table.md)).

**No gate check can catch this.** The entry is true; the problem is that its
stopping condition is satisfiable by a failure it was never meant to cover.

Shape of the fix, in preference order:

1. **Preconditions on stopping advice.** An entry that licenses "stop" must
   state what has to be *verified* first — here, that the placed object is the
   target, not merely that an object was placed. Structured `requires:` (issue
   5e) is the natural carrier, extended from "which tools" to "which
   verifications".
2. **Ledger signal.** Consumption crossed with outcome already exists; an entry
   consumed in N runs that all failed is a `negative` in the ledger's own
   vocabulary. This entry should surface there now.
3. **A gate lint for stopping verbs.** Entries whose body contains stop/abort
   advice get flagged for a human to check the precondition is discriminating.

Related revision: of the three t5 non-firings on record, **two are now explained
by the wrong object being placed**, so the flaky-checker claim itself rests on
less evidence than believed — the resident session's attempt-3 repeat alone.

## 5g. A perception budget, with the instrument counted inside it

Filed 2026-08-13 as the remedy for the **t1 regression** in generation 7
(0/3, diagnosed in [09 §4.1f](09-baseline-table.md)). **Not built** — the
method is frozen through the Friday delivery.

The diagnosis is that [issue 2](#2-two-sweep-runs-never-issued-a-motion-command)
has returned with a new channel. Motion calls stay flat at 9–12 across solved
and failed t1 runs while perception calls climb 32 → 153; the failures are not
acting less, they are looking more, and the turn budget is consumed by looking.
One run issued three motions across 167 calls, 44 of which were `segment` and
`inspect_image`.

The instrument is implicated but not indicted: t1's decline began when the
instrument was added (3/3 blind → 2/3 gen 6), one generation *before* the entry
revision that was initially suspected.

**Remedy shape**, in the order it should be tried:

1. **A perception budget** — after N perception calls without an advancing
   call, instruct the agent to commit to its best current estimate and say so
   in the audit. `ToolCallLimitMiddleware` is prebuilt.
2. **Count `inspect_image` inside that budget.** It is now part of the spiral,
   not an exemption from it — an instrument that can be queried indefinitely is
   another way to postpone acting.
3. **Shadow mode first**, per the standing rule for gates: log "this would have
   been capped", collect the trigger rate and the false-positive rate before
   anything is enforced, and keep the matched-pair data that makes a later A/B
   interpretable.

**The experiment that would settle attribution, parked.** Three passes cannot
separate "the instrument costs t1 specifically" from "the instrument costs
marginal cells generally" — t0 also slipped to 2/3 in generation 7. The clean
test is a t1-only vision-arm comparison with and without a perception cap,
n≥5 per side. Roughly 1–2 GPU hours. Not scheduled; GPU is reserved pending the
owner's decision on the full-matrix question.

## 5h. Procedural inflation, and the admission rate as a governed quantity

Filed 2026-08-14 from the full-benchmark generation 1 result
([09](09-baseline-table.md)). **Not built.**

Thirty-seven entries admitted in one batch cost eight cells across the
benchmark. The mechanism is *not* consultation cost — failed and successful runs
read the same amount (9.8 vs 8.7 entries). It is **procedural inflation**:
individually-correct entries compose into a procedure that issues **three times
the motions** (44 vs 13) and exhausts the turn budget in 8 of the 11 regressed
cells.

**Every gate check examines one proposal in isolation.** Nothing evaluates what
a batch demands collectively. That is the same class of defect as
[5f](#5f-a-gated-entry-became-an-excuse): true entry-by-entry, harmful in
composition.

Remedy directions, none built:

1. **A sixth check class — composed procedural cost.** Before applying a batch,
   estimate the procedure it prescribes: how many verification obligations does
   a run now carry, and what is their expected call cost against the turn
   budget? A batch that raises the floor above the budget is rejected as a
   batch, whatever its individual merits.
2. **The admission rate becomes a governed quantity.** It is currently an
   outcome of per-proposal judgement. It should be a declared parameter with a
   default and a justification for exceeding it.
3. **Cost-aware and tiered knowledge.** The deeper need behind
   [5e](#5e-the-one-line-library-index-with-conditions-as-its-key-and)
   — which is hereby **demoted from "the remedy" to "part of the remedy"**. An
   index makes the library cheaper to *consult*; it does nothing about a
   procedure that is too expensive to *execute*. Entries need a notion of when
   they are worth their cost, not merely when they apply.

**The experiment that separates dosage from content**: generation 1b, identical
in every respect but with a **pruned library of the twelve strongest entries**.
If it recovers toward generation 0's 53 while keeping `object_task`'s gain, the
finding is dosage. If it does not, the finding is content and the entries
themselves need revision. Roughly one benchmark pass; owner's call.

## 5i. `ToolCallIntegrityMiddleware` misses a DeepSeek-400 variant

Found in full-benchmark generation 1 (2026-08-14). Two runs died on
`BadRequestError: 400 — "An assistant me…"`, the orphan-`tool_calls` failure the
middleware was built to repair after the gen-0 `object_swap` sweep. **Its
pre-flight repair does not catch this variant**, and at benchmark scale that is
two lost cells per 80 rather than a curiosity.

Counted as failures, not excluded: unlike an external kill, the run constructed
the malformed request itself, and a harness crash is a harness result — the same
call made when the original 400 was first recorded.

The middleware already dumps the outbound request on provider rejection, so the
crime scene for both casualties exists on disk and has not yet been read. That
is the next step, and it is cheap.

## 6. `InjectionLedgerMiddleware`

`wrap_model_call`'s `ModelRequest` exposes `messages`, `system_message` and `tools` —
that is exactly what reaches the provider, so it is the anchor for per-component token
accounting without needing a proxy. Measured baseline to attribute against: initial
injection ~13.4k tokens (system 19.9k chars, tools 25.9k chars, user 1.1k chars).

## 7. `ProvenanceMiddleware` — argument-level evidence

`segment` already returns `world_path`, and the databus stores it per reading, so the
citation token exists. The check that matters: every numeric argument in an advancing
call traces to (a) a perception artifact, (b) a memory entry, or (c) invented by the
model. **The third bucket is the diagnostic** — "how often does the planner invent a
coordinate" is cheap to compute and hard to argue with.

## 8. Smaller items

- **`tests/harness/test_deep_agent.py` section A2 is order-fragile** (found
  2026-08-12 during the branch sync; observed failing once, then 3/3 clean, and
  **not reproduced in 15 further local runs** — so the defect is certain from
  the code but the rate is low and scheduling-dependent).

  The scripted turn 2 issues **two tool calls in one `AIMessage`**
  (`move_to` id `c2` and `pi0_pick` id `c3`, `test_deep_agent.py:111-113`).
  `ToolCallLogMiddleware` appends each record as its call completes, so
  `tool_calls.jsonl` order follows `ToolNode`'s execution order, which is not
  guaranteed to match the order the calls appear in the message. Three
  assertions assume it does:

  - `names == ["back_project", "move_to", "pi0_pick", "finish"]` — reports a
    check failure;
  - `recorded[1]["args"]["xyz"]` — **raises `KeyError`** when `pi0_pick` lands
    first, since its args carry `prompt`/`max_chunks` and no `xyz`. This is the
    observed crash;
  - the `step_idx` advancing check also indexes `recorded[1]` positionally,
    so it silently checks the wrong record.

  Fix shape: assert on `sorted(names)` (or a set) for the parallel pair, and
  look records up **by tool name** rather than by position for the argument and
  `step_idx` checks. Note the ordering itself is not a bug — the log is
  seq-ordered by completion and `call_id` is the join key precisely because
  position is unreliable (see 02-decisions, "The join is by call_id, not by
  position"). The test is asserting a property the design deliberately does not
  provide.
- **`tests/harness/audit_descriptions.py` is broken**: it does
  `git show HEAD:robots/libero/tools.py`, which no longer exists at HEAD. Pin it to
  `3c2516e` (the pre-split commit) if the description-drift check is wanted, or retire
  it now that the prompt has deliberately changed.
- **`tests/harness/retro.py` needs the log archive** at
  `tests/harness/realdata/` (six pre-refactor runs, not committed — 429 MB). Fetch
  from the box if the replay is needed again.
- **Legacy planner retirement.** `api_loop.py` / `claude_code.py` / `codex.py` and the
  `Toolkit.execute_tool` path still work via `legacy_specs.py`. When they go,
  `legacy_specs.py`, `LiberoToolkit._step` and the `_SPECS` machinery go with them, and
  `LiberoContext` becomes the only bookkeeping path.
- **`--interactive` on the deepagents planner** currently raises. LangGraph's
  human-in-the-loop interrupt is the equivalent.
- **Cross-camera mask fusion.** `segment` reads one camera's world map, and `rim` is
  documented as biased away from that camera. Segmenting the same entity in both
  cameras and fusing the two point sets should cancel much of that bias, needs no arm
  motion, and is the cheapest first step toward the multi-viewpoint merge skill the
  owner wants. Note OpenETA does not have this either.
- **`world_extent`'s `voxel` / `exclude_arm_radius` are exposed to the model.** Both
  are measured constants; letting the model tune them is letting it turn a knob it has
  no evidence for. Consider fixing them in the implementation and moving changes to
  configuration.
