---
title: Retry failed Pi0 picks from a clear/home viewpoint before giving up
type: technique
scope: common
conditions: When a pi0_pick empties the origin box but no object is in the hand; when
  an air-grasp or push is diagnosed after lifting; when the object is later found
  in a new footprint; when a re-pick from the original stance has failed.
support: 1
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_05.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=28
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=33
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=43
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=44
  counter_evidence:
  - run:20260807-16:08:47_libero_object_swap_t9_s0#seq=59
- action: revise
  proposal: logs/gate_gen3/proposals/proposal_04.md
  batch: gate_gen3
  date: '2026-08-10'
  evidence:
  - run:20260808-11:00:42_libero_object_swap_t0_s0#seq=68
  - run:20260808-11:00:42_libero_object_swap_t0_s0#seq=71
  - run:20260808-11:00:42_libero_object_swap_t0_s0#seq=77
  - run:20260808-11:00:42_libero_object_swap_t0_s0#seq=78
  - run:20260808-12:47:32_libero_object_swap_t9_s0#seq=34
  - run:20260808-12:47:32_libero_object_swap_t9_s0#seq=47
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen4/proposals/proposal_04.md
  batch: gate_gen4
  date: '2026-08-10'
  evidence:
  - run:20260810-17:57:07_libero_object_swap_t3_s0#seq=85
  - run:20260810-17:57:07_libero_object_swap_t3_s0#seq=87
  - run:20260810-17:57:07_libero_object_swap_t3_s0#seq=92
  - run:20260810-17:57:07_libero_object_swap_t3_s0#step=12
  counter_evidence: []
---

An air-grasp does not leave the object where it was. If the origin box empties but verification shows nothing held, scan the surrounding table for the object's new footprint before re-picking; the object may have been knocked over or displaced. Re-issue the pick from the fresh footprint, not from the original coordinates, and verify the retry geometrically before transport.
