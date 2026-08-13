---
title: When repeated pushes to a landmark do not terminate, re-identify the goal landmark
  before more attempts
type: failure_mode
scope: common
conditions: When several pushes, picks, or carries against the same segment all leave
  the episode running; when the vision label for the landmark changes between queries.
support: 1
provenance:
- action: add
  proposal: logs/gate_gen0full_libero_goal_swap/proposals/proposal_10.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-13:29:48_libero_goal_swap_t5_s0#seq=18
  - run:20260813-13:29:48_libero_goal_swap_t5_s0#seq=26
  - run:20260813-13:29:48_libero_goal_swap_t5_s0#seq=40
  - run:20260813-13:29:48_libero_goal_swap_t5_s0#seq=48
  - run:20260813-13:29:48_libero_goal_swap_t5_s0#seq=54
  - run:20260813-13:29:48_libero_goal_swap_t5_s0#seq=81
  - run:20260813-13:29:48_libero_goal_swap_t5_s0#seq=86
  counter_evidence: []
---

When several manipulation attempts against the same landmark all leave the episode running, re-validate that the landmark is the true goal before making more attempts. Segment/back-project the broader scene, probe occupancy above the landmark, and compare vision's label. A goal model built from one early segment can be wrong; a repeated no-termination pattern is the signal to reidentify.
