---
curated: gen1b_owner_order 2026-08-14
title: Do not conclude emptiness from a single tight occupancy box
type: failure_mode
scope: common
conditions: When an occupancy/compare_extent query with arm exclusion returns zero
  points directly beneath the EEF; when a zero reading is about to trigger a re-pick
  or a wrong conclusion.
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
- action: revise
  proposal: logs/gate_gen0full_libero_object_swap/proposals/proposal_06.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-12:16:54_libero_object_swap_t6_s0#seq=29
  - run:20260813-12:16:54_libero_object_swap_t6_s0#seq=73
  counter_evidence: []
---

WHEN: an occupancy or compare box reads zero or newly empty.
RULE: a zero taken with the arm in or near the box is not emptiness — the
arm-exclusion sphere can hide the object itself. Move the arm clear or
disable the exclusion, re-query once, then decide.
WHY: false re-picks of still-held objects measured.
