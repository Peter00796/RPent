---
title: Plate-center is tight; "right of the plate" means +y
type: invariant
scope: task
conditions: When planning either placement in the mug-and-pudding cell.
support: 2
provenance:
- action: add
  proposal: logs/20260815-10:42:41_libero_10_task_t6_s51/resident_notes.md
  batch: resident_10task_t6_r1
  date: '2026-08-15'
  evidence:
  - run:20260815-10:42:41_libero_10_task_t6_s51#seq=20
  - run:20260815-10:42:41_libero_10_task_t6_s51#seq=21
  counter_evidence: []
---

Two semantics, both measured: (1) "mug on the plate" is a tight xy match
on the plate CENTER (~1-2 cm), evaluated continuously — both solves
terminated at the moment a pick nudged the mug across the plate center,
not at a release. Aim the mug at the segmented plate-center, and know the
flag can fire mid-manipulation. (2) "right of the plate" is +y (the
camera frame's right, consistent with the dual-mug cell): pudding at
plate_y + 0.15, x-aligned, fires; +x and -y placements never fire, and
the table's +x edge (0.306) makes +x placement physically unsafe for the
8 cm pudding box anyway.
