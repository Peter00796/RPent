---
title: Release from above the rim with the gripper still closed; do not descend into
  the basket first
type: technique
scope: task
conditions: bottle-or-can verified held and carried to the basket; release phase
support: 1
provenance:
- action: add
  proposal: logs/resident_libero_object_swap_t5/mine_02_vision/proposals/proposal_03_release_recipe.md
  batch: resident_mine_02
  date: '2026-08-11'
  evidence:
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=41
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=42
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=74
  counter_evidence:
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=42
- action: revise
  proposal: logs/fix_5f_proposals/p2.md
  batch: fix_5f
  date: '2026-08-12'
  evidence:
  - run:20260812-12:06:23_libero_object_swap_t5_s0#seq=62
  - run:20260812-14:15:31_libero_object_swap_t5_s0#seq=38
  counter_evidence: []
---

Keep the above-rim release technique unchanged. CORRECT the checker claim:
of the three recorded non-firings on this cell, two are now explained by a
wrong-object placement — the checker was RIGHT both times. The flakiness
claim therefore rests on a single archived repeat (resident attempt 3) and
is UNCONFIRMED. Treat any non-firing as a contradiction per the env-tier
termination entry: verify the IDENTITY of what is actually in the basket
before attributing anything to the checker, and never end an episode as an
unqualified success on a silent flag.
