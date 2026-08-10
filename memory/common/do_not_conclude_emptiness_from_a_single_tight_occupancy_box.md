---
title: Do not conclude emptiness from a single tight occupancy box
type: failure_mode
scope: common
conditions: When a box or held-object query returns 0 points while the arm is inside
  or above the queried volume, after a pick, or when a basket-interior zero is being
  used to infer a missing object.
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
---

A 0-point result means the sensor did not see points in that volume at that instant, not that the volume is empty in the world. Before using such a reading to declare an object absent or lost, clear the view, move the arm out of the queried volume, widen the query, or re-check with the wrist camera. If after a pick the held-object query returns 0 but the origin box emptied and the object appears elevated in agentview, the pick is verified. Use a zero reading as one vote, never as proof of absence.
