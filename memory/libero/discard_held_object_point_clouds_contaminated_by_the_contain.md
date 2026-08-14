---
curated: gen1b_owner_order 2026-08-14
title: Discard held-object point clouds contaminated by the container near the basket
type: failure_mode
scope: env
conditions: When the wrist is over or near the basket and held_object returns a shape_warning,
  an implausibly wide span, or basket-contaminated points.
support: 7
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_08.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-14:18:46_libero_object_swap_t0_s0#seq=42
  - run:20260807-14:18:46_libero_object_swap_t0_s0#seq=45
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=47
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=48
  - run:20260807-15:52:13_libero_object_swap_t8_s0#seq=69
  - run:20260807-16:08:47_libero_object_swap_t9_s0#seq=40
  counter_evidence: []
- action: endorse
  proposal: logs/gate_gen3/proposals/proposal_11.md
  batch: gate_gen3
  date: '2026-08-10'
  evidence:
  - run:20260808-11:37:47_libero_object_swap_t3_s0#seq=8
  - run:20260808-11:37:47_libero_object_swap_t3_s0#seq=88
  - run:20260808-11:37:47_libero_object_swap_t3_s0#seq=89
  - run:20260808-11:37:47_libero_object_swap_t3_s0#seq=93
  counter_evidence: []
- action: endorse
  proposal: logs/gate_gen4/proposals/proposal_09.md
  batch: gate_gen4
  date: '2026-08-10'
  evidence:
  - run:20260810-18:51:12_libero_object_swap_t7_s0#seq=45
  - run:20260810-18:51:12_libero_object_swap_t7_s0#seq=46
  - run:20260810-19:07:57_libero_object_swap_t9_s0#seq=53
  - run:20260810-19:07:57_libero_object_swap_t9_s0#seq=54
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen0full_libero_object_task/proposals/proposal_04.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-10:17:41_libero_object_task_t3_s0#seq=12
  - run:20260813-10:17:41_libero_object_task_t3_s0#seq=7
  - run:20260813-10:34:08_libero_object_task_t5_s0#seq=13
  - run:20260813-10:34:08_libero_object_task_t5_s0#seq=14
  - run:20260813-11:19:24_libero_object_task_t8_s0#seq=10
  - run:20260813-11:19:24_libero_object_task_t8_s0#seq=5
  counter_evidence: []
---

WHEN: held_object near a container or surface.
RULE: clouds there mix in container points or vanish. Measure the held
offset once in open air right after the pick and reuse it for the whole
carry; never compute release coordinates from an over-container reading.
WHY: contaminated spans and vanishing clouds measured repeatedly.
