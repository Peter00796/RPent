---
title: Release the butter into the basket from the reachable floor and stop after
  the interior check
type: technique
scope: task
conditions: after the butter is carried to the basket; before the final descent/release
  motion
support: 1
provenance:
- action: add
  proposal: logs/practice_libero_object_swap_t6/round_01/proposals/proposal_02.md
  batch: round_01
  date: '2026-08-11'
  evidence:
  - run:20260811-11:11:12_libero_object_swap_t6_s52#seq=91
  - run:20260811-11:11:12_libero_object_swap_t6_s52#seq=93
  - run:20260811-11:11:12_libero_object_swap_t6_s52#seq=94
  - run:20260811-11:11:12_libero_object_swap_t6_s52#seq=97
  counter_evidence: []
- action: revise
  proposal: logs/resident_libero_object_swap_t6/mine_01/proposals/proposal_02.md
  batch: resident_mine_01
  date: '2026-08-11'
  evidence:
  - run:20260811-12:50:41_libero_object_swap_t6_s51#seq=9
  - run:20260811-12:50:41_libero_object_swap_t6_s51#seq=11
  - run:20260811-12:50:41_libero_object_swap_t6_s51#seq=12
  - run:20260811-12:50:41_libero_object_swap_t6_s51#seq=14
  counter_evidence: []
---

Do not go straight from the carry into a low descent. First transit to a pose above the basket opening, then descend while keeping the gripper command unchanged. Termination can fire during this descent; if it does, treat the episode as finished and issue no further motions, release commands, or re-scans. If no termination fires, complete the release at the clamp height and verify the basket interior once, then stop.
