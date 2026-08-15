---
title: Close with a crawl of low pitched pushes on the front bar
type: technique
scope: task
conditions: When the bowl is in the drawer and the drawer must be closed.
support: 2
provenance:
- action: add
  proposal: logs/20260815-10:10:41_libero_10_swap_t3_s51/resident_notes.md
  batch: resident_10swap_t3_r1
  date: '2026-08-15'
  evidence:
  - run:20260815-10:10:41_libero_10_swap_t3_s51#seq=33
  - run:20260815-10:10:41_libero_10_swap_t3_s51#seq=22
  counter_evidence: []
---

The close is a crawl of pushes on the drawer's FRONT BAR (top z ≈ 0.955),
with the fist AT bar height — pushes at eef z ≥ 1.0 float over the bar
and do nothing. Escalate the pitch push by push: pitch 0 → -0.5 → -0.8 →
-1.0, each a move_pose to (bar_x, bar_y+0.03, ~0.96-0.97) then a -y push
past the bar; the pitch -1.0 push reaches eef y ≈ -0.19 and fires
termination. Never pitch deeper than -1.0: at -1.2/-1.4 the fingers go
nearly horizontal ABOVE the bar top and miss it entirely.
