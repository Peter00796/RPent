---
title: Do not conclude emptiness from a single tight occupancy box
type: failure_mode
scope: common
conditions: When a tight occupancy box at the expected landing spot returns only floor
  points after a release; when a basket-interior zero is about to be used to start
  a re-pick.
support: 3
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_10.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-14:28:32_libero_object_swap_t1_s0#seq=79
  - run:20260807-14:28:32_libero_object_swap_t1_s0#seq=97
  - run:20260807-14:28:32_libero_object_swap_t1_s0#seq=109
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=10
  - run:20260807-15:15:22_libero_object_swap_t5_s0#seq=30
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen3/proposals/proposal_06.md
  batch: gate_gen3
  date: '2026-08-10'
  evidence:
  - run:20260808-12:27:43_libero_object_swap_t7_s0#seq=30
  - run:20260808-12:27:43_libero_object_swap_t7_s0#seq=31
  - run:20260808-12:34:51_libero_object_swap_t8_s0#seq=75
  - run:20260808-12:34:51_libero_object_swap_t8_s0#seq=76
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen4/proposals/proposal_02.md
  batch: gate_gen4
  date: '2026-08-10'
  evidence:
  - run:20260810-17:36:14_libero_object_swap_t1_s0#seq=73
  - run:20260810-18:58:23_libero_object_swap_t8_s0#seq=50
  - run:20260810-18:58:23_libero_object_swap_t8_s0#seq=52
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen5/proposals/proposal_05.md
  batch: gate_gen5
  date: '2026-08-11'
  evidence:
  - run:20260810-20:31:41_libero_object_swap_t4_s0#seq=44
  - run:20260810-20:31:41_libero_object_swap_t4_s0#seq=48
  - run:20260810-20:31:41_libero_object_swap_t4_s0#seq=61
  - run:20260810-20:31:41_libero_object_swap_t4_s0#seq=62
  counter_evidence: []
---

A tight box at the exact expected landing point can miss an object that is standing slightly offset, tilted, or occluded by the basket wall. The floor-only reading is one vote against placement; before re-picking, clear the arm, lower the wrist into view of the basket interior, and segment/back-project the object. Only if the object is still not inside the basket should the run treat the placement as failed and re-pick.
---
