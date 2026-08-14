---
curated: gen1b_owner_order 2026-08-14
title: When target-name segmentation fails, retry with color/shape prompts before
  declaring the object absent
type: technique
scope: common
conditions: When SAM3 text prompts for the target return found=false across several
  phrasings on either camera; when the target is visible but no name isolate it.
support: 3
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_01.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-14:18:46_libero_object_swap_t0_s0#seq=3
  - run:20260807-14:18:46_libero_object_swap_t0_s0#seq=5
  - run:20260807-15:52:13_libero_object_swap_t8_s0#seq=17
  - run:20260807-15:52:13_libero_object_swap_t8_s0#seq=20
  - run:20260807-15:21:05_libero_object_swap_t6_s0#seq=35
  counter_evidence:
  - run:20260807-14:28:32_libero_object_swap_t1_s0#seq=2
- action: revise
  proposal: logs/gate_gen0full_libero_object_task/proposals/proposal_01.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-09:29:18_libero_object_task_t0_s0#seq=5
  - run:20260813-09:29:18_libero_object_task_t0_s0#seq=53
  - run:20260813-10:02:20_libero_object_task_t2_s0#seq=29
  - run:20260813-11:05:14_libero_object_task_t7_s0#seq=32
  counter_evidence: []
---

WHEN: the target name fails to ground.
RULE: climb each rung once, then act: (1) two-three rephrases including
color/shape; (2) the other camera; (3) VLM pixel, back-projected — reject
it if z leaves the support surface; (4) point-prompt or low-z occupancy
elimination. After the ladder, act on the best-supported candidate.
WHY: this sweep's successful localizations came from leaving the naming
loop, not extending it.
