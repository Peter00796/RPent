---
title: Resolve semantic collisions with color and geometric probes before committing
  to a target
type: technique
scope: common
conditions: When several object-name prompts land on the same mask; when two identical
  instances must be told apart by distance/height to a named reference or support
  surface; when a second instance is being hunted after one complete sweep.
support: 4
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_02.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=2
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=6
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=10
  - run:20260807-15:15:22_libero_object_swap_t5_s0#seq=4
  - run:20260807-15:01:22_libero_object_swap_t4_s0#seq=20
  - run:20260807-16:08:47_libero_object_swap_t9_s0#seq=5
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen3/proposals/proposal_05.md
  batch: gate_gen3
  date: '2026-08-10'
  evidence:
  - run:20260808-11:58:02_libero_object_swap_t5_s0#seq=12
  - run:20260808-11:58:02_libero_object_swap_t5_s0#seq=13
  - run:20260808-11:58:02_libero_object_swap_t5_s0#seq=111
  - run:20260808-11:29:15_libero_object_swap_t2_s0#seq=11
  - run:20260808-11:29:15_libero_object_swap_t2_s0#seq=14
  - run:20260808-11:29:15_libero_object_swap_t2_s0#seq=46
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen4/proposals/proposal_03.md
  batch: gate_gen4
  date: '2026-08-10'
  evidence:
  - run:20260810-17:36:14_libero_object_swap_t1_s0#seq=90
  - run:20260810-17:36:14_libero_object_swap_t1_s0#seq=73
  - run:20260810-18:25:20_libero_object_swap_t5_s0#seq=12
  - run:20260810-18:25:20_libero_object_swap_t5_s0#seq=13
  - run:20260810-18:58:23_libero_object_swap_t8_s0#seq=44
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen0full_libero_spatial_task/proposals/proposal_02.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-12:54:46_libero_spatial_task_t1_s0#seq=82
  - run:20260813-13:07:06_libero_spatial_task_t2_s0#seq=43
  - run:20260813-13:21:24_libero_spatial_task_t6_s0#seq=49
  - run:20260813-13:28:44_libero_spatial_task_t8_s0#seq=17
  - run:20260813-13:31:27_libero_spatial_task_t9_s0#seq=5
  counter_evidence: []
---

When the category/color prompt cannot separate instances, measure the candidate's relation to the task reference: distance to the named object, or height relative to the named support surface. Select the candidate that matches the task's spatial relation, and treat the shared name prompt as corroboration only. Re-check before the pick with an independent point-prompt/back-projection probe or a second spatially-phrased segment.
