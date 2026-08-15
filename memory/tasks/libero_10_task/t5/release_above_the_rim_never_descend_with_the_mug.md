---
title: Release above the rim — never descend into the caddy with the mug
type: failure_mode
scope: task
conditions: When placing the held mug into the caddy, choosing the release height —
  and when planning the grasp.
support: 2
provenance:
- action: add
  proposal: logs/20260815-08:27:54_libero_10_task_t5_s51/resident_notes.md
  batch: resident_10task_t5_r1
  date: '2026-08-15'
  evidence:
  - run:20260815-08:27:54_libero_10_task_t5_s51#seq=13
  - run:20260815-08:27:54_libero_10_task_t5_s51#seq=27
  counter_evidence: []
---

Grasp: the mug body (0.10 m) is wider than the gripper's max opening
(0.078) — only pi0 can pick it (it finds the handle/rim wall); never
script a body grasp, and never let the mug escape the planned path (a
displaced mug defeats pi0 too — five re-picks failed). Place: descend
only to rim_z + 0.06 (fingers above the rim, mug bottom just inside the
opening, position corrected by the measured held offset) and release() —
the mug drops ~10 cm and seats. Descending further with the mug held
stalls at the rim (z≈1.07) and the OSC grind pushes the mug out over the
front wall onto the table.
