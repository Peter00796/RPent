---
title: Keep the mug body over the plate center — the checker region is tight
type: failure_mode
scope: task
conditions: During the descent and release of either mug onto its plate.
support: 2
provenance:
- action: add
  proposal: logs/20260814-15:47:45_libero_10_task_t4_s51/resident_notes.md
  batch: resident_10task_t4_r1r2
  date: '2026-08-15'
  evidence:
  - run:20260814-15:00:33_libero_10_task_t4_s51#seq=25
  - run:20260814-15:47:45_libero_10_task_t4_s51#seq=37
  counter_evidence: []
---

The checker's region is TIGHTER than the visual plate footprint: seatings
verified by point cloud 2-3 cm off-center did not fire it. The only fire
observed happened during a HELD, controlled descent with the mug body
directly over the plate center — termination can fire with the gripper
still closed, before any release. Vertical releases at these lateral
plate distances (|y| ≈ 0.3) tend to drag the mug during the stall —
placements that look seated can silently sit outside the region. So:
center to the measured plate center, descend slowly while still gripping,
and expect the flag mid-descent; treat any off-center landing as a miss
even if it looks fine.
