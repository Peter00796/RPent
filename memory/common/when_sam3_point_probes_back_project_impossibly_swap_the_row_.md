---
title: When SAM3 point probes back-project impossibly, swap the row/column interpretation
  before trusting the mask
type: technique
scope: common
conditions: When a point derived from a SAM3 mask back-projects far from all known
  objects or to an impossible depth; when the mask box convention is ambiguous.
support: 1
provenance:
- action: add
  proposal: logs/gate_gen0full_libero_object_task/proposals/proposal_08.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-11:24:22_libero_object_task_t9_s0#seq=20
  - run:20260813-11:24:22_libero_object_task_t9_s0#seq=22
  - run:20260813-11:24:22_libero_object_task_t9_s0#seq=25
  - run:20260813-11:24:22_libero_object_task_t9_s0#seq=27
  counter_evidence: []
---

A SAM3 mask box can be read as either [row0,col0,row1,col1] or [col0,row0,col1,row1]. When a point from a mask back-projects to an impossible location or disagrees with every other object, probe the same pixel with row/column swapped before concluding the mask is wrong or the object is absent. Corrected probes that agree with occupancy/back-projection are usable for grasp planning.
