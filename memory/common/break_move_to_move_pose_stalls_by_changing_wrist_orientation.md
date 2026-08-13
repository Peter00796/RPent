---
title: Break move_to/move_pose stalls by changing wrist orientation; do not repeat
  the same stalled move
type: technique
scope: common
conditions: When move_to or move_pose stops with a large residual distance; when the
  stall occurs with an unusual wrist pitch/yaw or after a low reach; when repeating
  the same move makes no progress; when a low-z approach stalls but a higher approach
  succeeds.
support: 4
provenance:
- action: add
  proposal: logs/gate_gen0full_libero_10_swap/proposals/proposal_09.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-15:52:15_libero_10_swap_t0_s0#seq=79
  - run:20260813-15:52:15_libero_10_swap_t0_s0#seq=83
  - run:20260813-15:52:15_libero_10_swap_t0_s0#seq=86
  - run:20260813-17:33:31_libero_10_swap_t3_s0#seq=27
  - run:20260813-17:33:31_libero_10_swap_t3_s0#seq=36
  - run:20260813-17:33:31_libero_10_swap_t3_s0#seq=40
  - run:20260813-17:32:49_libero_10_swap_t8_s0#seq=88
  - run:20260813-17:32:49_libero_10_swap_t8_s0#seq=93
  - run:20260813-19:02:53_libero_10_swap_t9_s0#seq=67
  - run:20260813-19:02:53_libero_10_swap_t9_s0#seq=91
  counter_evidence: []
---

A stalled move with a large residual is often an IK/configuration lock, not a distance problem. Repeating the same command in the same wrist pose will not make progress. Change the configuration: add explicit pitch/yaw targets to move_pose, rotate the wrist by about 90 degrees, back away to a higher z and approach again. Use a move_pose that co-varies position with wrist tilt when the arm is jammed near a low surface.
