# Baseline inventory — every arm we have actually run

> ## The counting convention — read this before quoting any number
>
> **A run solved iff some entry in its `states.json` carries the environment's
> own termination flag.** Nothing else counts as evidence of a solve.
>
> - **this framework**: `any(step["libero_terminated"] is True)`, where
>   `states.json` is a JSON **list** of step blobs.
> - **upstream RPent** (from `#73`, `rpent/tools/state.py`): the key is
>   `terminated`, not `libero_terminated`, and `states.json` is a **dict**
>   `{"run_artifacts": [...], "steps": [...]}`. Same env flag, different
>   shape — a counting script must handle both or upstream will silently
>   score zero.
> - **never** count from the agent's audit file (`{suite}_t{N}_s{S}.json`).
>   It is written only when the agent calls `finish`, so a run that solves and
>   then exhausts its turn budget scores as a failure. This is not
>   hypothetical: it costs us the t5 solve (`20260811-22:05:02`).
> - **never** count `pi0_pick.success` as anything. It is false on good grasps
>   and true on air grasps; both directions are demonstrated in
>   [08 §8.4/§9.2](08-draft-pr-narrative.md).
> - resident sessions: read each `attempt_NN/states.json` as well as the live
>   one; report per-attempt, not just per-run.
>
> **Interrupted runs are EXCLUDED, not scored.** A run is an interrupted
> measurement — invalid as a failure *and* as a solve — when **both** hold:
>
> 1. `run.log` contains **no natural-exit marker** (`FINISH called`,
>    `reached max_turns`, `without a tool call. Stopping`), and
> 2. its final timestamp coincides with a documented abort (a `pkill`, a
>    sweep cut, a relaunch of the same cell moments later).
>
> Both conditions are required. The `[agent] elapsed:`/`usage:` footer alone is
> too blunt a test: a run can exit naturally, log its marker and its recipe
> path, and still be cut during the last second of cleanup before the footer
> is written — that measurement is complete and counts. See §4.1c.

Written 2026-08-11 for the Friday draft PR, so that no number in the doc has to
be recalled. Every row here was recomputed from the run artifacts on the box on
2026-08-11; where it disagrees with an earlier note, this file is the one that
was checked and the disagreement is called out explicitly in
[§7](#7-corrections-this-recount-forced).

**Nothing here was re-run to produce it.** 322 existing run directories were
read; no GPU job was launched.

---

## 1. How "solved" was computed

Ground truth is the environment's own checker, as the harness recorded it:

```
solved(run) := any step in states.json has "libero_terminated": true
```

`states.json` is written by the harness per env step
([`robots/libero/tools/state.py`](../../robots/libero/tools/state.py)); the field
is copied from the env server's reply, not from anything the model said.

Two weaker signals were deliberately **not** used:

- the agent's own audit file (`{suite}_t{N}_s{S}.json`, the `libero_terminated`
  key inside it). It is written only when the agent calls `finish`, so a run
  that solved and then ran out of turns before writing its audit scores as a
  failure. This is not hypothetical: **`20260811-22:05:02_..._t5_s0` terminated
  at step 7 and wrote no audit.** An audit-based count loses that solve.
- `pi0_pick.success` — refuted, see [03-findings](03-findings.md).

Where a run has archived attempts (`attempt_NN/`, resident sessions), each
attempt's own `states.json` was read; a session counts as solving if any attempt
did, and the per-attempt breakdown is given.

The scan script is reproducible: it walks `logs/*`, reads the first
`physical agent cmd` line of `run.log` for the configuration (model, planner,
`--sandbox`, `--resident`, `--vision-tool`, `--experiment`, `--max-turns`) and
`sandbox.json` for the profile fingerprint.

Log roots:

| era | path (on `guangdong-b-is.cloud.infini-ai.com`) | dirs |
|---|---|---|
| pre-refactor | `/mnt/user_dir/pengyanxin/rpent_setup/rpent/logs` | 155 with a `run.log` (157 entries) |
| this framework | `/mnt/user_dir/pengyanxin/rpent_refactor/logs` | 157 (147 runs + 10 tool-output dirs) |

---

## 2. The configuration axes — what makes two runs a different arm

A result is only comparable to another result at the same point on all five
axes. Most of the confusion in earlier notes comes from comparing across one of
them silently.

| axis | values seen | where it is recorded |
|---|---|---|
| **planner** | `api` (pydantic-ai, pre-refactor) / `deepagents` (this work) | `run.log` line 1 |
| **model** | `deepseek:deepseek-v4-flash` (almost everything), `anthropic:claude-opus-4-8` (10 pre-refactor runs), `openai-chat:glm-5.2` (3) | `run.log` line 1 |
| **prompt era** | pre-cleansing (per-cell recipe blocks present) / cleansed / capability-leveled | commit date vs the run timestamp |
| **sandbox profile** | *(none — no sandbox existed)* / `none` / `memory` / `practice` | `sandbox.json` `profile` + `source_sha256` |
| **library state** | HF `RLinf/RPent-memory` (old) / clean-room gen0..gen5 / + task playbooks | commit `memory: generation N` |

Plus per-run switches: `--resident`, `--vision-tool`, `--experiment`.

### The prior-leak audit, measured

How many runs actually read a per-cell answer (`resources/libero/results_*_pert/`)
or the 187-constant lookup table (`env_calibration.md`), counted from `run.log`:

| era | n | read `results_*_pert` | read `env_calibration.md` |
|---|---|---|---|
| pre-refactor | 155 | **104** (67%) | 89 (57%) |
| this framework, before the sandbox | 11 | 1 (the 19:39 t2 run) | 11 (all) |
| this framework, sandbox on (`none`/`memory`/`practice`) | 136 | **0** | **0** |

That table is the sandbox's acceptance test, and it is the honest reason the
pre-refactor numbers are not a baseline for anything: two thirds of them read
the answer to the cell they were being scored on.

---

## 3. Pre-refactor era (upstream harness + our prompt of the time)

`--planner api`, no sandbox, prompt containing per-task `t0`–`t9` recipe blocks
(33,174 chars of `robots/libero/prompts/system.py` at box head `c639460`), HF
memory library present.

| model | n | solved | note |
|---|---|---|---|
| `deepseek:deepseek-v4-flash` | 141 | 93 (66%) | across `libero_object_swap` (108), `libero_goal_swap` (30), other (3) |
| `anthropic:claude-opus-4-8` | 10 | 10 | **not a head-to-head** — different cells, different dates, priors on |
| `openai-chat:glm-5.2` | 3 | 3 | same caveat |
| `anthropic:claude-opus-4.8` (typo'd id) | 1 | 0 | failed on the bad model id |

`libero_object_swap` seed 0, per cell, all pre-refactor runs:

```
t0 7/7   t1 4/7   t2 15/32  t3 2/7   t4 6/7
t5 4/7   t6 6/7   t7 6/7    t8 7/7   t9 4/7
```

**Read this table with the leak column in §2.** These are not "the model is
good at t0"; they are "the answer for t0 was on disk and 67% of runs read it".

> ⚠ The opus and glm rows are the only non-DeepSeek data that exists anywhere in
> this project, they are n=10 and n=3 on unmatched cells with priors available,
> and they cannot support any statement comparing model strength. **No
> head-to-head against a frontier model has ever been run.**

---

## 4. This framework — full `libero_object_swap` t0–t9 seed-0 sweeps

Every complete sweep, chronological. `deepseek-v4-flash`, `--planner deepagents`,
`--max-turns 50`, `--no-images` throughout.

| # | run dirs (first → last) | profile | library | n | solved | per cell |
|---|---|---|---|---|---|---|
| S1 | `20260806-23:57:08` → `20260807-01:12:20` | *(pre-sandbox)* | HF | 10 | **8** | `t0+ t1+ t2- t3- t4+ t5+ t6+ t7+ t8+ t9+` |
| S2 | `20260807-14:18:46` → `16:08:47` | `none` | — (gen 0) | 10 | **4** | `t0+ t1- t2+ t3+ t4- t5- t6- t7+ t8- t9-` |
| S3 | `20260807-18:33:42` → `20:35:04` | `memory` | gen 1 | 10 | **5** | `t0- t1+ t2- t3+ t4+ t5- t6- t7+ t8+ t9-` |
| S4 | `20260808-11:00:42` → `12:47:32` | `memory` | gen 2 | 10 | **7** | `t0+ t1- t2+ t3+ t4+ t5- t6- t7+ t8+ t9+` |
| S5 | `20260810-17:21:40` → `19:07:57` | `memory` | gen 3 | 10 | **6** | `t0- t1- t2+ t3+ t4+ t5- t6- t7+ t8+ t9+` |
| S6 | `20260810-19:40:14` → `21:29:44` | `memory` | gen 4 | 10 | **5** | `t0- t1+ t2+ t3- t4- t5+ t6- t7+ t8- t9+` |
| S7 | `20260810-21:45:48` → `23:29:28` | `none` | — | 10 | **6** | `t0+ t1+ t2+ t3+ t4- t5- t6- t7+ t8- t9+` |
| S8 | `20260810-23:34:08` → `20260811-01:13:20` | `memory` | gen 4 | 10 | **8** | `t0+ t1+ t2+ t3+ t4+ t5- t6- t7+ t8+ t9+` |
| S9 | `20260811-01:20:05` → `03:09:25` | `none` | — | 10 | **6** | `t0- t1+ t2+ t3+ t4+ t5- t6- t7+ t8+ t9-` |
| S10 | `20260811-03:19:41` → `05:12:33` | `memory` | gen 4 | 10 | **5** | `t0- t1- t2+ t3+ t4+ t5- t6- t7+ t8+ t9-` |
| S11 | `20260811-18:16:16` → `19:49:10` | `practice` | gen 5 + t5/t6 playbooks | 10 | **7** | `t0- t1+ t2+ t3+ t4+ t5- t6+ t7+ t8- t9+` |
| S12 | `20260811-19:49:27` → `20260812-02:06:53` | `practice` | same | 10 | **5** | `t0- t1+ t2+ t3- t4+ t5- t6- t7+ t8- t9+` — cut mid-pass, resumed 6 h later; see §4.1c |
| S13 | `20260811-22:41:11` → `20260812-00:40:16` | `none` | — | 10 | **6** | `t0+ t1+ t2+ t3- t4- t5- t6- t7+ t8+ t9+` (**P2**) |
| S14 | `20260812-02:15:33` → `04:08:00` | `practice` | same | 10 | **6** | `t0- t1+ t2+ t3+ t4- t5- t6+ t7+ t8- t9+` (**P3** pass 3) |
| V1 | `20260812-09:26:21` → `11:09:30` | `practice` **+ `--vision-tool`** | same | 10 | **9** | `t0+ t1+ t2+ t3+ t4+ t5+ t6+ t7+ t8+ t9-` |
| V2 | `20260812-11:19:55` → `12:56:23` | `practice` **+ `--vision-tool`** | same | 10 | **7** | `t0+ t1+ t2+ t3+ t4+ t5- t6- t7+ t8+ t9-` |
| V3 | `20260812-13:06:12` → `15:04:39` | `practice` **+ `--vision-tool`** | same | 10 | **8** | `t0+ t1- t2+ t3+ t4+ t5- t6+ t7+ t8+ t9+` |

> **S12's apparent duplicate t4 is resolved by exclusion, not preference** —
> the first copy was externally killed and is not a measurement. Evidence chain
> in §4.1c.

### 4.1 The comparisons that are actually licensed

**Repeats, n=3 per arm** — the only paired numbers in the project:

| arm | runs | scores | mean | spread |
|---|---|---|---|---|
| `none` (no library at all) | S7, S9, **S13** | 6, 6, 6 | **6.0** | **0** |
| `memory` @ gen 4 | S6, S8, S10 | 5, 8, 5 | **6.0** | ±1.73 |
| `practice` (gen 5 + t5/t6 playbooks) | S11, S12, **S14** | 7, 5, 6 | **6.0** | ±1.0 |
| **`practice` + `--vision-tool`** | **V1, V2, V3** | **9, 7, 8** | **8.0** | ±1.0 |
| *(retired)* `none` @ gen-0 head | S2 | 4 | — | bug-affected, see below |

### Three of the four arms sit at 6.0/10; the vision arm is the first to move

**The library produces no measurable suite-wide lift** — `none`, `memory` and
blind `practice` are indistinguishable at 6.0. Adding the vision instrument to
the `practice` arm moves it to **8.0 ± 1.0**, and that comparison is the one
controlled experiment in this project (§4.1d). Everything below about the
library's flatness still stands: it is the *instrument*, not the library, that
moved the mean. The earlier +0.7 reading was the
`none` arm's mean being dragged down by S2, and P2 (S13) was run specifically
to test that: a `none` sweep at current head scored **6**, giving the no-library
arm `6, 6, 6` with **zero spread**. The old `4` is now positively identified as
the casualty it was suspected to be — it predates `f4a36c72` (08-07 16:22), the
fix for the DeepSeek-400 orphan-`tool_calls` crash, and its t5 run logs two
400-family errors and dies at 216 k input tokens where its siblings spent
4.0–6.6 M. **S2 is retired from the arm** and kept only as the record of a
harness bug.

So: the generational curve is dead, and so is the suite-mean claim that replaced
it. Anyone quoting "the memory library is worth +0.7 cells" is quoting an
artifact of a fixed crash.

### 4.1a Where the library *is* worth something: one cell at a time

The value is **cell-targeted, not suite-wide**, and the same data that kills the
mean shows it clearly:

| cell | clean-room history | `none` arm (S7,S9,S13) | `practice` arm, all exams |
|---|---|---|---|
| **t6** | **0/11** | **0/3** | **5/6** — 3/3 seed-0 exams, S11 ✓@2, S12 ✗, S14 ✓@13 |
| **t5** | 3/16 all arms | 0/3 | **0/3 blind** (S11, S12, S14) · **1/2 with `--vision-tool`** |

t6 is a cell that eleven consecutive clean-room runs could not touch and that
the no-library arm still cannot touch, now solved five times in six attempts by
an arm whose only difference is four gated playbook entries. **That** is the
result. It is invisible in a suite mean because the suite mean is dominated by
middle-band variance on cells the library neither helps nor hurts.

t5 is the control on the other side: its decisive entries are
**arm-dependent** — they presuppose a vision channel — so a blind arm carrying
them scores 0/3 while the vision-armed exam solved. Knowledge that the tool
surface cannot execute is not knowledge for that arm.

Stratified across the older arms, the middle band (t0/t1/t4/t8/t9) is where all
the noise lives; the easy cells (t2/t3/t7) do not need the library and the hard
cells do not yield to it without the matching instrument.

### 4.1d The vision ablation — the one controlled comparison in the project

`practice` vs `practice + --vision-tool`: same sandbox, same library, same
model, same turn budget, same ten cells, n=3 per side. **`--vision-tool` is the
only variable.** Nothing else in this file is this clean.

| | blind (S11, S12, S14) | vision (V1, V2, V3) | Δ |
|---|---|---|---|
| suite | 7, 5, 6 → **6.0 ± 1.0** | 9, 7, 8 → **8.0 ± 1.0** | **+2.0** |

Per cell, and this is where the result actually lives:

| cell | blind | vision | Δ | reading |
|---|---|---|---|---|
| **t0** | 0/3 | **3/3** | **+3** | unpredicted; see below |
| t1 | 3/3 | 2/3 | −1 | noise |
| t2 | 3/3 | 3/3 | 0 | saturated |
| t3 | 2/3 | 3/3 | +1 | noise |
| t4 | 2/3 | 3/3 | +1 | noise |
| **t5** | 0/3 | 1/3 | +1 | the designed target — **moved weakly, and not for the reason the design predicted** |
| t6 | 2/3 | 2/3 | 0 | **knowledge-bound, predicted vision-indifferent — confirmed** |
| t7 | 3/3 | 3/3 | 0 | saturated |
| **t8** | 0/3 | **3/3** | **+3** | unpredicted; see below |
| **t9** | 3/3 | 1/3 | **−2** | the pre-registered cost outcome — **but not from instrument turn-burn** |

**The entire suite gain is t0 and t8.** +3 and +3 against a net +6; every other
cell nets to zero (t3 +1, t4 +1, t5 +1, t1 −1, t9 −2). That is a much sharper
attribution than a mean, and it is not what the pre-registration predicted.

#### Against the pre-registered predictions (filed before any number existed)

| prediction | outcome |
|---|---|
| t5 should move (designed target) | **partly wrong** — 0/3 → 1/3, and its two failures are not vision failures (§4.1e) |
| t6 unchanged (knowledge-bound) | **correct** — 2/3 → 2/3 |
| t1/t2/t7/t9 saturated, unchanged | **wrong for t9** (3/3 → 1/3); correct for the rest |
| t3/t4 noise ±1 | correct (both +1) |
| t0/t8 — declined to predict | 0/3 → **3/3** each, and they are the whole gain |

So the mechanism model was **wrong about where the instrument's value would
show**. It was predicted to pay off on the cell it was built for and to be
irrelevant elsewhere; instead it barely moved that cell and carried two others
entirely. Declining to predict t0/t8 was the right call — and the reason those
two were unpredictable is that nobody had ever diagnosed why they failed.

One pre-commitment has to be applied to its author: *"the one number I'd
distrust on sight is a big suite-mean jump without t5 moving."* That is
literally what happened. The rule does not fire only because the movement is
**not** middle-band noise — it is concentrated in two chronic zeros, +3 each,
which noise at n=3 cannot manufacture. Recorded rather than quietly dropped.

#### What the instrument was doing in t0 and t8

Established from the records: `inspect_image` was called in **all six** t0/t8
runs (t0: 10, 7, 4 calls; t8: 16, 2, 14), and in both cells it is used **early
and for object identity discrimination** — the designed role:

```
t0 seq 15/116  "What is it? Choose from: a red alphabet soup can, a y…"
t8 seq 14/96   "Which item is the chocolate pudding — de…"
```

**Not established: causation.** No matched pairs exist (the blind runs are
different runs, not a paired counterfactual), and some of the instrument's
answers in these very runs are **wrong** — t0 seq 15 calls the target "a white
cream cheese tub". So the honest statement is: the instrument was present, used
in its designed role, and both cells went 0/3 → 3/3; *why* is the next
diagnostic target, and it wants a matched read of one blind t0 failure against
one vision t0 solve. **No causal story is asserted here.**

#### The t9 regression, and the cost hypothesis it refutes

t9 was pre-registered as the shape a *cost* finding would take: turns burned on
instrument calls. **The records do not support it.** Of the two t9 failures,
`20260812-12:56:23` made **zero** `inspect_image` calls, and both failures used
exactly 46 tool calls each. A cell cannot lose to instrument turn-burn in a run
that never called the instrument. The regression is real (3/3 → 1/3) and
**unexplained**; it is the second item on the diagnostic list.

#### ⚠ Three runs were armed but never used the instrument

`20260812-11:43:27` (t2, solved), `20260812-12:56:23` (t9, failed) and
`20260812-14:34:26` (t6, solved) carried `--vision-tool` and called
`inspect_image` **zero** times. They are functionally blind runs sitting in the
vision column. So "the only variable is the flag" is exactly true and
"the only variable is the behaviour" is not: **3/30 vision-arm runs behaved as
blind runs.** Surfaced by the counter's instrument-usage check, which exists
for precisely this failure mode; recorded because it slightly softens the
ablation's cleanliness and a reader deserves to know the direction (it makes
the +2.0 a mild *under*-statement of what using the instrument is worth, and a
mild over-statement of what arming it is worth).

### 4.1e t5 adjudicated — the instrument was right and the planner overruled it

t5 went 0/3 blind → **1/3** with the instrument. Both failures were adjudicated
with `t5_adjudicate.py` under the procedure fixed **before the sweep produced a
number**, and both came back `UNDETERMINED` from the tool — correctly, because
the tool refuses to convert a keyword screen into a verdict. Reading the
records settles them, and the answer is neither 2a nor 2b as originally framed:

**The instrument was correct. The planner overrode it.**

Ground truth, established by the solved run `20260812-10:22:09`: the target is
a **silver can with a red/green label** at `[-0.118, -0.241]`; the brown bottle
at `[-0.19, -0.07]` reads **"TANGY BBQ SAUCE"**.

Both failures picked the bottle at `[-0.19, -0.07]` — the BBQ distractor:

- `20260812-12:06:23` moved to the bottle and picked it. The VLM had already
  said so: seq 45 *"It looks like a BBQ sauce bottle (dark brown)"*, seq 59
  *"Brown … Not legible … Brown"*. The agent overrode it with an availability
  argument, in its own audit: *"since the env guarantees a pickable
  tomato_sauce_1 and exactly one bottle exists on the table, the standing bottle
  was taken as the tomato sauce."*
- `20260812-14:15:31` did the same, `move_to [-0.19, -0.074, 0.21]` then pick,
  reasoning to *"the scene's only small bottle"*.

**The inference is the failure.** The tomato sauce is a *can*; "the only
bottle" is the distractor by construction. The instrument said brown/BBQ and
was talked out of it.

#### The finding that matters most, and it is against us

Both runs then explained their non-firing checker by **citing our own playbook
entry**:

> `20260812-12:06:23`: *"libero_terminated did NOT fire — the documented flaky-checker behavior on this cell; per the playbook I stopped instead of re-seating a bottle already in the basket."*
>
> `20260812-14:15:31`: *"matching the documented flaky checker on this cell (an above-rim drop is the recipe that normally fires it, and one repeat is on record as also failing). Per the memory playbook, after confirming…"*

The checker was **right**: the agent had put the BBQ bottle in the basket. But
the library contained a gated, evidence-backed entry saying *this cell's checker
is flaky, verify once and stop*, and that entry supplied a **ready-made,
honest-sounding explanation for a wrong-object failure**. Both failures took it,
wrote a confident audit, and stopped.

**A gated entry became an excuse.** That is an unintended consequence of grown
knowledge that no check in the gate would catch: the entry is true, its
citations resolve, its numbers trace, and it was admitted correctly. It is
nonetheless capable of terminating a run that should have kept looking. Filed
as a new open issue — the shape of the fix is that a "stop, the checker is
flaky" entry must carry a precondition that the *right object* was verified,
not merely that *an* object was placed.

This also revises the flaky-checker claim itself: of the three t5 non-firings
now on record, **two are explained by the wrong object being placed.** The
genuine flaky-checker evidence is thinner than
[§5.2](#52-t5--pick-the-tomato-sauce-and-place-it-in-the-basket-the-perception-channel-wall-two-visually-near-identical-sauce-bottles)
implies, and rests on the resident session's attempt-3 repeat alone.

### 4.1b A predicted contamination, now observed

Both blind t5 sweep runs (`20260812-00:53:35`, `20260812-03:15:06`) read **all
five** t5 playbook entries at seq 5–9, with **`inspect_image` call count 0** —
the tool is not on a blind arm's surface. One of those entries, the
owner-edited `localize_extra_bottle_clusters_geometrically_not_by_color_la.md`,
instructs the agent to *"`back_project` the pixel and require the returned z to
sit near table level"* — a procedure that presupposes a VLM pixel the blind arm
cannot obtain.

This is exactly the arm-dependence scenario [issue 5e](04-open-issues.md)
predicted when the `requires:` filter was specified. Both runs failed — but
**the transcripts have not been read, so no causal claim is made**: what is
established is that the *predicted exposure occurred*, not that it cost
anything. The motivation for the `requires`-filtered per-run index moves from
anticipated to empirical; its impact remains unquantified.

**Resolution (2026-08-12).** The vision sweep puts those same entries on an arm
that *can* execute them: all three t5 vision runs called `inspect_image`, and
the cell went 0/3 → 1/3. So the exposure is no longer arm-inappropriate for t5.
But the resolution is narrower than it looks — §4.1e shows both remaining
failures had **correct** instrument output and lost to planner inference, so
putting executable knowledge on an executing arm was necessary and not
sufficient. And the same sweep produced the sharper version of the same problem
in the other direction: an entry that *is* executable on this arm
(the flaky-checker recipe) actively supplied a wrong explanation. Arm-matching
the library fixes what a run *can* do, not what it *should conclude*.

### 4.1c Interrupted runs — the exclusion register

A run that was killed mid-flight is not a failure; it is a missing
measurement. Applying the two-condition test from the counting convention to
**every** run directory in the corpus turns up exactly four, all recorded here
so a future recount does not silently re-admit them.

| run | steps | natural-exit marker | verdict |
|---|---|---|---|
| `20260811-20:34:31_..._t4_s0` | 17 | **none** | **EXCLUDED** — externally killed |
| `20260811-18:02:28_..._t0_s0` | 17 | **none** | **EXCLUDED** — aborted, relaunched 45 s later |
| `20260811-12:52:17_..._t6_s51` | 0 | **none** | **EXCLUDED** — aborted launch, 20 s long |
| `20260812-01:11:00_..._t6_s0` | 16 | `reached max_turns=50` | **VALID — counts as a failure** |

**The t4 exclusion, in full**, because it is the one that changes a published
number. `20260811-20:34:31_libero_object_swap_t4_s0`:

- `run.log` contains **zero** `[agent] elapsed:` / `usage:` footer lines and
  **zero** natural-exit markers — no `finish`, no `reached max_turns`, no
  essay-drift stop;
- it ends mid-tool-result at **20:46:50** (`[tool<] segment: {"found": true,
  "step": 16, …}`), with 17 step records and climbing;
- that timestamp coincides with a documented abort: a `pkill -f rpent.cli.main`
  issued at ~20:46–47 to end the sweep and start the vision arm, whose session
  launched at **20:48:01**.

So it belongs to the same category as the sweep-cut itself — an interrupted
measurement, invalid as a failure *and* as a solve. **The `20260812-00:46:00`
resumption run is the only valid t4 in pass 2**, and it solved. Pass 2 is
therefore **5/10**, and the practice arm is `7, 5, 6` → mean **6.0**.

**Why the footer alone is not the test.** `20260812-01:11:00_..._t6_s0` has no
footer either, and it is a *valid* failure: it logged
`reached max_turns=50. Stopping.` and its recipe path at 01:40:37, then died in
the last second of cleanup before the footer was written. The measurement was
complete. A one-condition "no footer ⇒ exclude" rule would have deleted a real
failure and inflated the practice arm — which is why the convention requires
both a missing marker **and** abort provenance.

**Footnote: what killed it was our own bug, and it is now fixed.** Chasing the
cleanup crash produced a traceback in the chain log:

```
File "rpent/cli/main.py", line 139, in <listcomp>
  {**{k: v for k, v in m.items() if k != "content"},
AttributeError: 'HumanMessage' object has no attribute 'items'
```

`_serialize_messages` assumed every transcript message is a dict. The nudge
path injects `("user", nudge)`, which LangChain materialises as a
`HumanMessage` object, and the transcript is written in the run's final block —
so the run died **after** its recipe was saved and **lost its transcript
entirely**. Blast radius, counted rather than assumed: **1 confirmed
occurrence** out of 26 nudged runs (25 nudged runs wrote transcripts fine, so
the trigger is narrower than "a nudge happened" and is not fully
characterised). The other transcript-less run in the register, `18:02:28`, has
no traceback and never reached the recipe write — it was killed, not crashed.

Fixed on this branch: `_serialize_messages` now coerces non-dict messages
(`model_dump()` when available, otherwise a typed repr) instead of raising,
because the transcript is evidence — replay reads its reasoning text — and an
unknown message shape recorded is worth more than an exception.

Two of the other three exclusions were already outside every table in this
file, but only by where the globs happened to start. They are registered here
so that is a decision rather than an accident.

### 4.2 Per-cell, pooled across full sweeps

Retired `none` sweep S2 excluded (see §4.1); interrupted runs excluded per
§4.1c; `practice` pools S11/S12/S14.

| cell | `none` (S7,S9,S13) | `memory` (S3–S6,S8,S10) | `practice` blind (S11,S12,S14) | `practice`+vision (V1–V3) | pre-sandbox (S1) |
|---|---|---|---|---|---|
| t0 | 2/3 | 2/6 | 0/3 | **3/3** | 1/1 |
| t1 | 3/3 | 3/6 | 3/3 | 2/3 | 1/1 |
| t2 | 3/3 | 5/6 | 3/3 | 3/3 | 0/1 |
| t3 | 2/3 | 5/6 | 2/3 | 3/3 | 0/1 |
| t4 | 1/3 | 5/6 | 2/3 | 3/3 | 1/1 |
| t5 | 0/3 | **1/6** | **0/3** | **1/3** | 1/1 |
| t6 | **0/3** | **0/6** | **2/3** | 2/3 | 1/1 |
| t7 | 3/3 | 6/6 | 3/3 | 3/3 | 1/1 |
| t8 | 2/3 | 5/6 | 0/3 | **3/3** | 1/1 |
| t9 | 3/3 | 4/6 | 3/3 | **1/3** | 1/1 |

The only column that moves against the `none` arm by more than noise is **t6**
(0/3 → 2/3 in-sweep, 5/6 counting the seed-0 exams). t0 and t8 move the *other*
way, which is the noise being noise.

### 4.3 The upstream-vanilla baseline (P1) — 8/10, and what buys it

Run 2026-08-12 from a bundle of upstream `RLinf/RPent` main at **`5da2573f`**,
cloned standalone to `/mnt/user_dir/pengyanxin/rpent_upstream`. **A different
codebase**, so it is not an S-number: `--planner api` (pydantic-ai),
`--model deepseek:deepseek-v4-flash`, `--no-images`, `--max-turns 50`, no
sandbox (upstream has none), HF priors sync left **on** — that is vanilla.

| | result |
|---|---|
| solved | **8/10** — `t0+ t1+ t2- t3+ t4- t5+ t6+ t7+ t8+ t9+` |
| termination key | `terminated` (upstream shape — see the counting convention) |
| **prior reads** | **112 calls across 10/10 runs** |
| cost | 45 min agent time, 15.8 M in / 224 k out |
| audits | 5 runs wrote none; **3 of them solved** — audit-based counting would have scored this 5/10 |

**The 8/10 is purchased, and the receipt is legible.** The clearest single case
is t5 — the cell our entire vision arc was spent on
([§5.2](#52-t5--pick-the-tomato-sauce-and-place-it-in-the-basket-the-perception-channel-wall-two-visually-near-identical-sauce-bottles)).
Upstream solved it at **env step 2**. What it read, and what it then did, in
full:

```
reads:  results_object_pert/object_swap_t5_s0.json      x3   <- the answer for this exact cell
        results_object_pert/recipe_object_swap_t5_s0.jsonl x2
        env_calibration.md                              x2
commands issued:
  step 1  pi0_pick("pick up the tomato sauce", max_chunks=25)
  step 2  pi0_pick("pick up the tomato sauce", max_chunks=25)   -> terminated: true
```

**No `segment`. No localisation. No perception of any kind.** Two identical
policy calls, replayed off the stored solution. The same cell defeated our blind
arms 0/3 and cost a resident session, a vision instrument and three
owner-adjudicated entries to crack once.

That is not a criticism of upstream — the priors are part of its design, and
with them available this is the rational thing for an agent to do. It is the
reason the number cannot be read as a harness measurement:

| arm | score | what it measures |
|---|---|---|
| upstream-vanilla, priors on | **8/10** | the value of the stored answers |
| our clean-room floor (`none`, n=3) | **6/10** (6, 6, 6) | what the model + tools can do with no answers |
| our `practice` arm (n=3) | **6.0** suite mean | same, plus grown knowledge — no suite-wide lift |
| our grown knowledge, per cell | t6 **0/11 → 5/6** | what a measured, gated recipe is worth where it applies |

Removing the answer files costs **two cells**. Winning cells back afterwards has
to be done by a mechanism.

#### The head-to-head the owner asked for

| arm | score | n | what it is made of |
|---|---|---|---|
| upstream-vanilla, priors on | **8/10** | 1 | its own prompt, its planner, **112 answer-file reads across 10/10 runs** |
| ours, `practice` + vision, clean-room | **8.0 ± 1.0** (9, 7, 8) | 3 | cleansed prompt, always-on sandbox, **0 prior reads**, grown+gated library, VLM instrument |

**Level, and reached from opposite directions.** Upstream's 8 is the stored
solution replayed — on t5 it is literally two `pi0_pick` calls and no
perception. Ours is 8.0 with the answer files unreachable by construction, and
it is the mean of three passes rather than a single sweep.

Stated carefully, because it is the sentence a reviewer will test hardest:
**this is a design-vs-design comparison, not a controlled one.** The two sides
differ on prompt, planner, priors access, turn accounting and timeout
simultaneously. What it licenses is *"the harness reaches the answer-fed
score without the answers, and does it three times"*; what it does not license
is any per-component attribution. The controlled result is §4.1d, and it is a
different claim: **+2.0 from the instrument alone, single variable.**

**Caveats, recorded rather than chased:**

- P1 ran roughly **2× faster per cell** than our arms (123–548 s vs 145–896 s).
  Expected: recipe replay is short, and it is a *consequence* of the priors, not
  an independent finding.
- Its two failures (t2, t4) are cells our arms also find middling. No anomaly.
- P1 differs from our arms on several axes at once — prompt, planner, priors
  access, turn accounting, and upstream's `CELL_TIMEOUT_S=1200` wall-clock cap,
  which our deepagents runs do not have. **It is the honest "before", not a
  controlled ablation.** The controlled comparisons remain §4.1.
- n=1. A single upstream sweep; no repeats were run.

### 4.3 Cost of one sweep (S11, measured)

```
10 runs, 93 min wall clock, 64 min of agent time
input  29.6 M tokens (DeepSeek automatic prefix cache ~93% hit)
output    409 k tokens
tool calls 643
```

Per run: 145 s – 748 s, 0.55 M – 7.7 M input, 15 k – 88 k output.

---

## 5. Single-cell arms — the t6 and t5 case studies

### 5.1 t6 — *"Pick the butter and place it in the basket"*

**All 23 seed-0 runs ever, both eras:**

| era / regime | runs | solved |
|---|---|---|
| pre-refactor, per-cell answer file read | `20260806-01:47`, `-01:53`, `-15:03`, `-15:09` | **4/4** |
| pre-refactor, no answer file (but pre-cleansing prompt + HF library) | `20260806-01:37`, `-15:16`, `-15:28` | 2/3 |
| this framework, pre-sandbox | `20260807-00:37` | 1/1 |
| **this framework, clean-room** (`none`/`memory`/`practice`, cleansed prompt) — 08-07 15:21 through 08-11 06:45 | 11 runs | **0/11** |
| this framework, after the resident-session revisions (`cfb35066`) | `20260811-13:48`, `-14:02`, `-14:19` (exams), `-19:15` (in sweep S11) | **4/4** |

Termination steps of the four post-fix solves: 8, 15, 7, 2.

**Cross-seed, `practice` profile, playbook-armed, single attempt:**
`t6_s1` fail (21 env steps, 120 calls), `t6_s2` solved @ step 9, `t6_s3` solved
@ step 7 → **2/3**.

**Practice-seed work behind the fix** (all `practice` profile, seeds ≥ 51):

| what | runs | result |
|---|---|---|
| amnesiac practice loop (control arm) | `20260811-10:14`, `-10:33`, `-10:54`, `-11:11`, `-11:31`, `-11:47`, `-12:18`, `-12:21` | 0 solves, 2 playbook entries, ended "no new knowledge" |
| `--experiment` episodes | `20260811-05:27`, `-06:07`, `-06:20`, `-12:08`, `-12:35` | 2 solves (s52 @ step 2, s51 @ step 7) — these are the localisation + grasp-prompt cracks |
| **resident session** `--resident` | `20260811-12:50:41_..._t6_s51` | attempt 1 solved @ step 8, attempt 2 solved @ step 6; 74 calls total |

### 5.2 t5 — *"Pick the tomato sauce and place it in the basket"* (the perception-channel wall: two visually near-identical sauce bottles)

**All 16 seed-0 runs, this framework:**

| profile / arm | n | solved |
|---|---|---|
| pre-sandbox | 1 | 1 (`20260807-00:29:54`, @ step 7) |
| `none` | 3 | 0 |
| `memory` | 6 | 1 (`20260810-20:46:39`, @ step 8) |
| `practice`, blind | 4 | 0 |
| `practice` + `--vision-tool` | 2 | **1** (`20260811-22:05:02`, @ step 7) |

**Practice-seed work on t5** (all `practice` profile, seeds ≥ 51):

| run | arm | outcome |
|---|---|---|
| `20260811-05:33:43_t5_s51` | `--experiment` | no solve, 1 env step, 15 calls |
| `20260811-06:29:45_t5_s53` | `--experiment` | no solve, 3 env steps, 48 calls |
| `20260811-15:06:00_t5_s51` | `--resident`, **blind** | no solve, 66 calls. **Died at turn 19 of 150**: two consecutive turns emitted no text and no tool call, each consuming exactly 8,192 output tokens (`max_tokens`) inside the hidden reasoning channel. The model's own turn-16 line: *"Wrist probes on A are all within noise (tomato 0.551, bbq 0.574, red 0.637, brown 0.602) — language cannot separate the two sauce bottles."* This is the "no measuring channel" exhibit, and the motivation for `f9fcc18e` |
| `20260811-20:48:01_t5_s51` | `--resident --vision-tool` | see below |

**Resident vision session** `20260811-20:48:01_..._t5_s51` (`--resident
--vision-tool`, 201 tool calls, 3 attempts):
attempt 1 fail (22 calls) → **attempt 2 solved @ step 13** (14 calls) →
attempt 3 fail (11 calls). **1/3 attempts within one session** — the honest
form of "the vision arm cracked t5".

#### The knowledge pincer — the two seed-0 vision exams

The two `--vision-tool` exams are **the same cell, same seed, same profile, same
model, same reader, same flags, 27 minutes apart**. The only variable is the
library:

| | `20260811-21:38:36` | `20260811-22:05:02` |
|---|---|---|
| playbook | 2 entries (proposals 1–3 still **held at the gate**) | **5 entries** (owner-adjudicated batch applied, `8e83affa`) |
| result | FAILED, 17 env steps, 83 calls, `max_turns=50` exhausted, no `finish` | **SOLVED @ env step 7**, 70 calls, in=3.1 M |
| what happened | picked the **brown BBQ** distractor and placed it, unaware; `inspect_image` caught it in-episode at seq 43/45 (*"BROWN … not the red of tomato sauce"*); recovery re-pick air-grasped (`success: true`, `min_gripper_opening 0.0020`, seq 72); budget ran out | all 5 task entries read at seq 5–9; distractor discriminated by label text (seq 39: *"Label text: 'TOMATO' and 'SAUCE'"*); `pi0_pick success: false` overruled geometrically; above-rim release per the hand-written recipe |

This is the closest thing in the project to an isolated measurement of the
marginal value of gated knowledge. **It is n=1 on each side.**

> The t5 headline claims rest on n=1 solves. t5 is *not* a never-solved cell:
> it also fell twice **blind** (S1 pre-sandbox and S6 `memory`), so it is 3/16
> on seed 0 across all arms. The environment checker is also demonstrably flaky
> on this cell — the admitted release recipe declares it in its own
> `counter_evidence` (an above-rim repeat did not fire the flag). Defensible:
> "t5 fell to the vision instrument plus three adjudicated entries, n=1, on a
> cell with a flaky checker." Not defensible: "vision solved t5."

---

## 6. Non-run artifacts on the box worth citing

| dir | what |
|---|---|
| `logs/gate_gen1` … `gate_gen5` | the five HARNESS_REVIEW cycles; local copies in `replays/gate_reviews/` |
| `logs/practice_libero_object_swap_t6` | the amnesiac control loop's `history.json` |
| `logs/resident_libero_object_swap_t6`, `_t5` | resident session notes (`resident_notes.md`) |
| `logs/playbook_t6`, `playbook_t6b` | playbook mining output |

Library state at `8e83affa`: **21 general entries** (14 `memory/common`,
7 `memory/libero`) + **9 task-playbook entries** (5 under
`memory/tasks/libero_object_swap/t5`, 4 under `…/t6`), plus
`memory/LEDGER.json` consumption records.

---

## 7. Corrections this recount forced

Recorded because they change claims already written down elsewhere.

1. **"t6: 0/11 on seed 0 all-time" is wrong as stated** (07-handoff line 53,
   line 121). It is 0/11 **in the clean-room era**. t6 seed 0 was solved 6/7
   times before the sandbox, including 4/4 runs that read
   `resources/libero/results_object_pert/object_swap_t6_s0.json` — the answer
   for that exact cell. The corrected claim is *stronger*, not weaker: the
   sandbox took the answer away, the cell went dead for 11 runs, and the
   harness re-derived a working recipe by measurement. It just has to be said
   that way.
2. **The `none` arm's three sweeps span code heads** (§4.1) and one of them
   predates a crash fix. Flagged, not corrected — re-running S2 at head is a
   proposal, below.
3. **Audit-file scoring loses at least one solve** (the t5 vision run). Any
   number computed from `{suite}_t{N}_s{S}.json` rather than `states.json`
   should be recomputed.
4. Pre-refactor run count is **155 with logs** (157 directory entries), not 156.
5. **S2 is now positively identified, not merely suspected** (P2, 2026-08-12).
   A `none` sweep at current head scored 6, making the arm `6, 6, 6` with zero
   spread. S2's `4` was the fixed-crash casualty, and the `+0.7 cells` the
   library appeared to be worth was an artifact of it. **Retired from the arm.**
6. **S12 duplicates t4** under a byte-identical configuration, once failing and
   once solving, because the pass was cut and resumed. Reported as a range
   (4–5/10) rather than resolved in the favourable direction; the conservative
   copy is used in every mean.

---

## 8. Gaps — PROPOSALS, none of them run, none to be run without a decision

Cost model from §4.3: one 10-cell sweep ≈ **95 min wall clock, ~30 M input /
0.4 M output DeepSeek tokens**. One single-cell run ≈ 5–12 min.

| # | gap | why it matters | cost | recommendation |
|---|---|---|---|---|
| ~~P1~~ **DONE** | **Upstream-vanilla + `deepseek-v4-flash`, sandbox off, t0–t9 s0** — the actual "before" of this PR, never measured. Everything we call a baseline already contains our prompt work. | A reviewer will ask "what did upstream score?" and we currently cannot answer. Nearest proxy is the pre-refactor era, which is leak-contaminated. | ran 45 min | **Ran 2026-08-12 → 8/10**, with 112 prior reads across 10/10 runs. See §4.3: the score is purchased with per-cell answer files, and t5 shows it at its starkest (solved at step 2 by two `pi0_pick` calls and zero perception). |
| ~~P2~~ **DONE** | **`none` arm re-run at current head** (S2 replacement) | Removes the code-head confound from `4,6,6`; the current no-library floor is really only n=2 (S7, S9). | 1 sweep ≈ 95 min | **Ran 2026-08-12 as S13 → 6/10.** It did repair the number, and the repair killed the +0.7 claim: see §4.1. |
| ~~P3~~ **DONE** | **Finish the cut passes 2 and 3 of the `practice` sweep** | `practice` is currently n=1 complete sweep (7/10) + a 2/6 fragment. The fragment is worse than the same six cells in S11 (S11 t0–t5: **4/6**; S12 t0–t5: **2/6**), so "7/10" as a headline is on thin ice. | ran ≈ 3.5 h | **Ran 2026-08-12 → S12 5/10, S14 6/10** (one interrupted run excluded, §4.1c). The practice arm is `7, 5, 6` — mean **6.0**, i.e. level with the no-library floor. Suite-wide lift: none. Cell-targeted lift on t6: large. See §4.1a. |
| P4 | **`--vision-tool` arm on the full suite** | Two runs exist, both on t5. Nothing supports a general claim about the vision channel. | 1 sweep ≈ 95 min + VLM calls | Only if the vision decoupling is a headline claim in the PR. |
| P5 | **t6/t5 cross-seed at n≥5** | 2/3 and 1/3 are the current transfer evidence. | 5 runs/cell ≈ 1 h | Cheap; upgrades "it transferred" from anecdote. |
| P6 | **A frontier-model head-to-head** | Zero data exists. | high (API cost, and the arm has to be built) | **Do not.** The claim in the doc is "cheap models + a grown harness crack cells the same cheap model alone cannot" — that needs no frontier comparison, and any such comparison we could afford would be underpowered. |

Owner decision needed on P1–P3 before any GPU time is spent. P6 is a
recommendation *against*.
