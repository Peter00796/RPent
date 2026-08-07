---
title: Treat large remaining distance on move_to as a stall; retreat and re-approach
type: failure_mode
scope: env
conditions: Applies when a move_to finishes with a large remaining distance, or when
  low correction moves become pinned near a rim, wall, or obstacle.
support: 4
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_11.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-14:44:02_libero_object_swap_t2_s0#seq=19
  - run:20260807-14:44:02_libero_object_swap_t2_s0#seq=24
  - run:20260807-14:44:02_libero_object_swap_t2_s0#seq=32
  - run:20260807-16:08:47_libero_object_swap_t9_s0#seq=14
  - run:20260807-15:52:13_libero_object_swap_t8_s0#seq=65
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=36
  counter_evidence: []
---

A move_to can report completion while lagging the requested target; a large remaining distance means the position controller did not arrive. Continuing to send small corrections from a pinned or wall-adjacent pose wastes steps. Retreat to clear space, re-localize the object and container, and plan a segmented approach; use a direct pose move for the final descent into the basket.
---
