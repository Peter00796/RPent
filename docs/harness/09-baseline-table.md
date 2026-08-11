# Baseline inventory — every arm we have actually run

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
| S12 | `20260811-19:49:27` → `21:38:36` | `practice` | same | **6 of 10** | 2 | `t0- t1+ t2+ t3- t4- t5-` — **CUT by the owner to save tokens** |

### 4.1 The comparisons that are actually licensed

**Repeats at (approximately) one code head, n=3 per arm** — the only paired
numbers in the project:

| arm | runs | scores | mean | spread |
|---|---|---|---|---|
| `none` (no library at all) | S2, S7, S9 | 4, 6, 6 | **5.33** | ±1.15 |
| `memory` @ gen 4 | S6, S8, S10 | 5, 8, 5 | **6.0** | ±1.73 |

Effect ≈ **+0.7 cells out of 10, against a per-sweep spread of ±1.5**. n=3.
This does not clear its own noise floor and must never be quoted as a single
number without the spread. Stratified, the difference is concentrated in the
middle band (t0/t1/t4/t8/t9: 9/15 with the library vs 7/15 without); the easy
cells (t2/t3/t7) do not need it and the hard cells (t5/t6) it cannot save.

**⚠ Caveat this recount surfaced, not previously recorded**: the three `none`
sweeps are *not* at one code head. S2 ran 2026-08-07 14:18, three days and ~30
commits before S7/S9, and **predates `f4a36c72` (08-07 16:22), the fix for the
DeepSeek-400 orphan-`tool_calls` crash**. S2's t5 run logs two 400-family errors
and dies at 216 k input tokens where its siblings in the same sweep spent
4.0–6.6 M — i.e. at least one of S2's six failures is a harness bug that no
longer exists. So the `none`
arm's `4,6,6` is better read as `[bug-affected 4], 6, 6`, and part of the
apparent gen-0→later growth is the harness code improving, not the library.
S7 and S9 are the clean pair for the `none` arm.

### 4.2 Per-cell, pooled across full sweeps

| cell | `none` (S2,S7,S9) | `memory` (S3–S6,S8,S10) | `practice` (S11,S12) | pre-sandbox (S1) |
|---|---|---|---|---|
| t0 | 2/3 | 2/6 | 0/2 | 1/1 |
| t1 | 2/3 | 3/6 | 2/2 | 1/1 |
| t2 | 3/3 | 5/6 | 2/2 | 0/1 |
| t3 | 3/3 | 5/6 | 1/2 | 0/1 |
| t4 | 1/3 | 5/6 | 1/2 | 1/1 |
| t5 | 0/3 | **1/6** | 0/2 | 1/1 |
| t6 | 0/3 | **0/6** | **1/1** | 1/1 |
| t7 | 3/3 | 6/6 | 1/1 | 1/1 |
| t8 | 1/3 | 5/6 | 0/1 | 1/1 |
| t9 | 1/3 | 4/6 | 1/1 | 1/1 |

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

---

## 8. Gaps — PROPOSALS, none of them run, none to be run without a decision

Cost model from §4.3: one 10-cell sweep ≈ **95 min wall clock, ~30 M input /
0.4 M output DeepSeek tokens**. One single-cell run ≈ 5–12 min.

| # | gap | why it matters | cost | recommendation |
|---|---|---|---|---|
| P1 | **Upstream-vanilla + `deepseek-v4-flash`, sandbox off, t0–t9 s0** — the actual "before" of this PR, never measured. Everything we call a baseline already contains our prompt work. | A reviewer will ask "what did upstream score?" and we currently cannot answer. Nearest proxy is the pre-refactor era, which is leak-contaminated. | 1 sweep ≈ 95 min. ×3 for a mean ≈ 5 h | **Highest value per GPU-minute.** But needs an upstream checkout on the box — it is not just a flag. Ask before spending. |
| P2 | **`none` arm re-run at current head** (S2 replacement) | Removes the code-head confound from `4,6,6`; the current no-library floor is really only n=2 (S7, S9). | 1 sweep ≈ 95 min | Cheap and it repairs a number we already quote. Recommended. |
| P3 | **Finish S12/S13** — the cut passes 2 and 3 of the `practice` sweep | `practice` is currently n=1 complete sweep (7/10) + a 2/6 fragment. The fragment is worse than the same six cells in S11 (S11 t0–t5: **4/6**; S12 t0–t5: **2/6**), so "7/10" as a headline is on thin ice. | 4 remaining runs of S12 + 10 for S13 ≈ 2.2 h | Recommended before the practice arm is quoted at all. |
| P4 | **`--vision-tool` arm on the full suite** | Two runs exist, both on t5. Nothing supports a general claim about the vision channel. | 1 sweep ≈ 95 min + VLM calls | Only if the vision decoupling is a headline claim in the PR. |
| P5 | **t6/t5 cross-seed at n≥5** | 2/3 and 1/3 are the current transfer evidence. | 5 runs/cell ≈ 1 h | Cheap; upgrades "it transferred" from anecdote. |
| P6 | **A frontier-model head-to-head** | Zero data exists. | high (API cost, and the arm has to be built) | **Do not.** The claim in the doc is "cheap models + a grown harness crack cells the same cheap model alone cannot" — that needs no frontier comparison, and any such comparison we could afford would be underpowered. |

Owner decision needed on P1–P3 before any GPU time is spent. P6 is a
recommendation *against*.
