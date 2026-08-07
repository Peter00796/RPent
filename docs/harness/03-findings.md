# Measured findings

Everything here came from real data — either replaying the new tools over six
pre-refactor runs, or reading a live run's logs. Synthetic clouds proved the maths;
only real point clouds exposed the defects.

The replay harness is [`tests/harness/retro.py`](../../tests/harness/retro.py).
It recovers each mask from the stored overlay (the overlay blended masked pixels as
`0.55*original + 0.45*red`, so a diff against the source image is the mask) and
recomputes from the stored world map. Sanity anchor: **recomputed `world_xyz`
matched the recorded value to 0.00 mm**, which is what licenses trusting the
recovered masks.

## Defects found on real data, and fixed

### 1. Mask edge-bleed inflated every `shape` extent, up to 6x

A mask's boundary pixels straddle the object edge, and their depth lands on
whatever is behind. Untrimmed min-max extents:

| object | untrimmed | trim 1% | trim 5% |
|---|---|---|---|
| soup can | **0.398 m** | 0.067 | 0.070 |
| salad dressing | **0.243** | 0.062 | 0.062 |
| woven basket | **0.329** | 0.196 | 0.190 |

Trimming the farthest 1% from the 3D median fixes it, and 5% moves it only 3 mm
further, so the outliers are very few and very extreme. A real 0.142 m bottle loses
2 mm. After trimming the readings are physically sensible for the first time, and
three separate round cans all land at 0.063 x 0.063 with `yaw_is_meaningful: False`
— the degeneracy guard working on real data.

Axis-aligned `bbox_3d` overstates the fitted long extent by a **median 1.14x, max
8.09x**.

### 2. `shape` could label the narrow axis "long" — the dangerous kind

Axes were ordered by *variance* while the reported extents were *min-max ranges*,
and those orders disagree when a tail is longer than the bulk is wide. Result:
`graspable_width_m` came out as the LARGER number, which would tell the planner a
6 cm bottle needed a 24 cm gripper span. Axes are now ordered by the extent actually
reported; ratio tests still use standard deviations, because a square footprint's
fitted axes land on its diagonals and min-max would make a 0.09 cube read as
"lying".

### 3. `world_extent(mode="held_object")` reported the tabletop as a grasped object

Its candidate window is a cylinder 2-20 cm below the eef, so a low eef swallows the
table. Of **25 closed-gripper steps across six runs, 12 were readings of a surface**
— one 12 cm wide (the full window), one 1 cm thick over 7 cm (a stove top). Rejected
now when the blob reaches the window's floor clamp or is a thin wide slab. A third
signal (wider than the gripper can span) only *warns*, because it fired
inconsistently on marginal cases and there is no ground truth here for which steps
were truly holding — falsely reporting "not holding" is its own harm.

## Findings that changed the prompt

### Gripper width does not detect a grasp

One run held **0.047 for five consecutive steps** while the point cloud found
nothing below the eef for the first three and 18k/20k points for the last two.
`Rule 1b`'s old heuristic ("0.01-0.05 gap ⇒ holding") gives the same answer for all
five, and is wrong for three.

### `pi0_pick.success` is false precisely when pre-positioning is good

Its predicate requires a descent of at least 10 cm. On the successful DeepSeek run:

```
lift     0.164 >= 0.08  ✓
gripper  0.0368 < 0.06  ✓
descent  0.088 >= 0.10  ✗   ← only this one
=> success = False
```

The agent had pre-positioned at z=0.20 with the bottle top at 0.146, so the descent
was 8.8 cm. **The flag penalises the behaviour the prompt teaches.** That run
survived only because the agent verified geometrically instead; an agent that
trusted the flag would have concluded its single attempt had failed.

### Held-object offsets are not constants (independent reproduction)

Within a single run the offset magnitude spanned **1.0-4.1 cm** on one run and
2.0-2.4 cm on another. This independently reproduces the claim the geometry PR was
built on, on different runs. `eef_y = plate_y + 0.045` in the old prompt was a
single measurement promoted to a constant.

## `compare_extent`: what it does and does not establish

**Do not compare across a whole episode.** Point count inside one fixed box swung
**1723 → 87282 (50x)** purely because the wrist camera ended up closer, so voxel
counts tracked how much the cameras saw rather than what was there. Net change did
not even agree in sign with the outcome (one solved run read -139, another +309).

**Adjacent steps are stable.** Four releases all read +78..+146 voxels added against
3..14 removed, with similar point counts on both sides.

**But it does not separate success from failure.** On those four releases the
signature was indistinguishable between the two runs that solved and the two that
never terminated — matter arrived inside the container box in all four, because an
object perched on the rim registers like a seated one. The tool answers whether the
world changed where you aimed; only the environment's checker answers whether the
task is done.

## Analysis of the first successful DeepSeek run

`20260806-19:39:33_libero_object_swap_t2_s0` — solved in 6 env steps, 17 model
turns, 27 tool calls, 181 s, on a cell that failed twice historically (24 and 17
steps, never terminated).

**It leaned on a prior solution to the identical cell.** WORKFLOW step 3 told it to
read `resources/libero/results_object_pert/object_swap_t2_s0.json` and its recipe —
same suite, same task, same seed. Side by side:

| | historical recipe | what the agent did |
|---|---|---|
| 1 | `move_to [-0.185, -0.088, **0.20**]` | `move_to [-0.1835, -0.0796, **0.20**]` |
| 2 | `pi0_pick "pick up the salad dressing" max_chunks=**10**` | identical, verbatim |
| 3 | — | `set_gripper +1 steps=8` (new) |
| 4 | — | intermediate waypoint (new) |
| 5 | `move_to [0.076, 0.231, **0.35**]` | `move_to [0.061, 0.245, **0.35**]` |
| 6 | `release` | `release` |

`max_chunks=10` against a schema default of 24, and both z heights, are the
reference's. The reference's `strategy_notes` also handed over the fact the task
turns on: which of two similar red bottles satisfies the predicate — a fact that is
not perceptually derivable and that the reference run itself needed a reset to
learn.

**What IS attributable to the new tools**: the grasp verification. The reference has
no such step, and it rescued the run from `pi0_pick.success=false`. The agent used
`compare_extent` on the box where the bottle *was*, looking for voxels removed —
the adjacent-step usage, which it worked out from the tool description. It also
applied the measured 1.55 cm held-object offset to the release point.

**Correction to an earlier reading of this run**: the two SAM3 scores (0.785 and
0.891) came from two *different* prompts finding two *different* objects, not from
the decoy outscoring the target on one prompt. Segmentation discriminated correctly
and its assignment matched the reference's independently — so that cell looks more
tractable without priors than first stated.

### Token and cache behaviour

```
in 1,010,018 / out 14,176 / cache_read 942,976 (93%) / cache_write 0 / 17 requests
per-request input:  req1 17,665 → req5 50,515 → req10 65,773 → req17 79,878
```

DeepSeek's automatic prefix caching works and is worth 93%; `cache_write=0` is
expected for server-side automatic caching. **Without the provider-native fallback
in `_provider_cache_tokens` this would have logged 0 cache hits.**

Context grew from 17.7k to 79.9k over 17 turns — roughly 3.9k of tool results per
turn. Fine at 17 turns; untenable at `--max-turns 100`.

**41% of tool calls were file reading** (9 `read_text_file` + 2 `list_dir` of 27).

## Remote sweep on the new framework

`/mnt/user_dir/pengyanxin/rpent_refactor/logs`, `libero_object_swap` t0-t9 plus one
earlier t2: **9/11 solved**.

**The t0-t9 sweep was prior-free.** Reading the transcripts for every
`read_text_file` / `list_dir` call: only the earlier 19:39 t2 run touched
`results_*_pert/` (6 calls). All ten sweep runs read **none** — so they ran on the
cleansed prompt, after WORKFLOW step 3 was removed. The clean headline is therefore
**8/10 on t0-t9 with no per-cell answers available**, using only `MEMORY.md`, the
guides, and the tools.

What every sweep run did read: `MEMORY.md` (11/11), `strict_hybrid_guide.md` (11/11),
`pro_hybrid_guide.md` (11/11), **`env_calibration.md` (11/11)** — the last one is
blocked as of `6e8b857`, so the sweep predates that commit and the next one will be
cleaner still. Plus 2-4 leaf memory files each, all technique-shaped
(`feedback_staged_held_object_transport`, `feedback_pi0_false_positive_lift`,
`feedback_pi0_pick_full_prompt`, `feedback_pi0_pre_pos_can_hurt`, the basket-placement
patterns).

One of those leaves is worth flagging: **`feedback_bowl_eef_y_offset.md`** is the
`+0.045` constant that measurement has since refuted. Deleting it from the prompt did
not delete it from the memory library.

```
t2 (19:39)  SOLVED@6     t5  SOLVED@7
t0          SOLVED@7     t6  SOLVED@9
t1          SOLVED@8     t7  SOLVED@2
t2 (00:10)  FAILED       t8  SOLVED@9
t3          FAILED       t9  SOLVED@8
t4          SOLVED@7
```

**Both failures share one signature: the agent spent its whole turn budget on
perception and never issued a single motion command.**

```
t2 failure: 6 turns / 22 calls — segment x14, motion x0, finish=null
t3 failure: 9 turns / 37 calls — segment x24 + world_extent x4, motion x0, finish=null
```

This is plausibly a side effect of the prompt cleansing: the new prompt strongly
mandates "localize everything, register every entity, pass the READY CHECK before
acting", and without a per-cell recipe to anchor on, it may not converge. **Verify
before the next sweep** — see `04-open-issues.md`.

## HuggingFace resource sync

`ensure_resources` calls `snapshot_download(repo_id="RLinf/RPent-memory",
local_dir=resources_dir.parent, allow_patterns=["libero/**"])` on **every run**.

Two findings:

1. **It failed at least once and was swallowed.** One run logged
   `could not sync 'libero' from 'RLinf/RPent-memory': 429 Client Error: Too Many
   Requests` and continued with local files. `snapshot_download` failing partway
   leaves `resources/` in a *partially* updated state — some files new, some stale —
   and the warning understates that.
2. **It overwrites local `resources/libero/` every run.** So deleting the priors
   locally does not stick; they are reinstalled on the next run. Any locally
   curated memory is clobbered, and pre-existing `results_*` may have been
   overwritten by the pull.

Since what lives on HF *is* the magic-numbers-and-priors payload, the sync is not a
convenience — it is the delivery mechanism for the thing the cleansing removed. See
`04-open-issues.md` item 1.
