---
title: Close the drawer with two 50-chunk pushes
type: technique
scope: task
conditions: When the bottle is placed and the bottom drawer must be closed.
support: 2
provenance:
- action: add
  proposal: logs/20260814-15:44:20_libero_10_task_t3_s51/resident_notes.md
  batch: resident_10task_t3_r2
  date: '2026-08-15'
  evidence:
  - run:20260814-15:44:20_libero_10_task_t3_s51#seq=25
  - run:20260814-15:44:20_libero_10_task_t3_s51#seq=34
  counter_evidence: []
---

pi0_doubled("close the drawer") with max_chunks=30 moves the panel only
~5 cm and never finishes (7 pushes measured). The slide completes with
max_chunks=50 from a clean south start: two 50-chunk pushes in a row
reached the closed threshold (panel/eef y ≈ 0.19) and fired termination.
Scripted move_pose pushes stall at the arm's low-z reach — use the
contact skill, not scripted pushing.
