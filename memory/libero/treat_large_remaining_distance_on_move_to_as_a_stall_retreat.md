---
curated: gen1b_owner_order 2026-08-14
title: Treat large remaining distance on move_to as a stall; retreat and re-approach
type: failure_mode
scope: env
conditions: Applies when a move_to finishes with a large remaining distance, or when
  low correction moves become pinned near a rim, wall, or obstacle.
support: 5
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
- action: endorse
  proposal: logs/gate_gen5/proposals/proposal_06.md
  batch: gate_gen5
  date: '2026-08-11'
  evidence:
  - run:20260810-19:56:09_libero_object_swap_t1_s0#seq=8
  - run:20260810-19:56:09_libero_object_swap_t1_s0#seq=75
  - run:20260810-19:56:09_libero_object_swap_t1_s0#seq=82
  - run:20260810-19:56:09_libero_object_swap_t1_s0#seq=91
  counter_evidence: []
---

WHEN: stalls at low z or near the robot base.
RULE: avoid low-z move_to near the base; step in small increments
(especially along -y); use a pitched move_pose for final descents. After
any stall, verify position before acting from it.
WHY: reachability boundaries measured; releases from stalled poses
missed.
