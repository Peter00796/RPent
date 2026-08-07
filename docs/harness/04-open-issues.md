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
