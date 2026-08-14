---
curated: gen1b_owner_order 2026-08-14
title: Do not treat a name-based segment result as identity ground truth
type: invariant
scope: common
conditions: When two task-name prompts return the same mask; when object labels are
  unreadable; when candidates share a category or color name; when a generic name
  is being reused for several instances.
support: 4
provenance:
- action: add
  proposal: logs/gate_gen2/proposals/proposal_01.md
  batch: gate_gen2
  date: '2026-08-08'
  evidence:
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=2
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=6
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=7
  - run:20260807-15:52:13_libero_object_swap_t8_s0#seq=3
  - run:20260807-15:52:13_libero_object_swap_t8_s0#seq=17
  - run:20260807-20:15:39_libero_object_swap_t7_s0#seq=15
  - run:20260807-20:15:39_libero_object_swap_t7_s0#seq=17
  - run:20260807-19:38:26_libero_object_swap_t5_s0#seq=16
  - run:20260807-19:38:26_libero_object_swap_t5_s0#seq=17
  - run:20260807-19:38:26_libero_object_swap_t5_s0#seq=22
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen0full_libero_10_swap/proposals/proposal_01.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-15:52:15_libero_10_swap_t0_s0#seq=2
  - run:20260813-15:52:15_libero_10_swap_t0_s0#seq=3
  - run:20260813-16:37:01_libero_10_swap_t4_s0#seq=4
  - run:20260813-16:37:01_libero_10_swap_t4_s0#seq=5
  - run:20260813-18:43:04_libero_10_swap_t7_s0#seq=3
  - run:20260813-18:43:04_libero_10_swap_t7_s0#seq=6
  - run:20260813-19:02:53_libero_10_swap_t9_s0#seq=2
  - run:20260813-19:02:53_libero_10_swap_t9_s0#seq=3
  counter_evidence: []
---

WHEN: identity comes from a text prompt.
RULE: found=true is a hypothesis, found=false is not absence, and two
prompts landing on one mask are one object. Before a pick that depends on
identity, confirm with one independent channel: a label read or geometry
against a task anchor.
WHY: SAM3 collapse measured at 39% on hard scenes; the unique-bottle
inference picked the distractor twice.
