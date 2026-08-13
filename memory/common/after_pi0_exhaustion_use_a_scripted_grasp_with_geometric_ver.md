---
title: After pi0 exhaustion, use a scripted grasp with geometric verification
type: technique
scope: common
conditions: When a scripted vertical pinch or descent stalls above a low or lying
  target; when move_to/move_pose stops short of the requested height repeatedly.
support: 2
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_06.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-15:01:22_libero_object_swap_t4_s0#seq=47
  - run:20260807-15:01:22_libero_object_swap_t4_s0#seq=54
  - run:20260807-15:21:05_libero_object_swap_t6_s0#seq=96
  - run:20260807-15:21:05_libero_object_swap_t6_s0#seq=100
  counter_evidence:
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=38
- action: revise
  proposal: logs/gate_gen2/proposals/proposal_09.md
  batch: gate_gen2
  date: '2026-08-08'
  evidence:
  - run:20260807-18:33:42_libero_object_swap_t0_s0#seq=87
  - run:20260807-18:33:42_libero_object_swap_t0_s0#seq=88
  - run:20260807-19:58:43_libero_object_swap_t6_s0#seq=94
  - run:20260807-19:58:43_libero_object_swap_t6_s0#seq=98
  - run:20260807-19:07:14_libero_object_swap_t2_s0#seq=71
  - run:20260807-15:01:22_libero_object_swap_t4_s0#seq=47
  - run:20260807-15:01:22_libero_object_swap_t4_s0#seq=54
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen0full_libero_object_task/proposals/proposal_05.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-10:38:55_libero_object_task_t6_s0#seq=81
  - run:20260813-10:38:55_libero_object_task_t6_s0#seq=87
  - run:20260813-10:38:55_libero_object_task_t6_s0#seq=90
  counter_evidence: []
---

A scripted vertical pinch on a low or lying target can stall several centimetres above the requested height because of the controller's effective floor. Treat the first stall as information; do not repeat the same descent with only a lower target. Retreat, re-localize, and change approach geometry — a horizontal side-grasp closes on different faces and avoids the vertical reach limit. A scripted grasp still requires geometric verification before transport.
