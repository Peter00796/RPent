---
title: Do not conclude emptiness from a single tight occupancy box
type: failure_mode
scope: common
conditions: Applies when an occupancy query returns zero points for a boxed region
  while other evidence suggests the region may be occupied.
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
---

A zero-point occupancy result is a function of box bounds, viewpoint, and occlusion, not a ground-truth statement about the scene. The arm itself can zero a box. Corroborate emptiness with a second view, larger/quadrant boxes, or segmentation; an empty origin box alone neither proves a grasp nor disproves occupancy.
---
