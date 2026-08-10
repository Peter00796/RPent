---
title: Verify every pi0 pick geometrically before transport
type: failure_mode
scope: common
conditions: Applies after any pi0_pick call, regardless of the tool-reported success
  status.
support: 11
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_03.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-14:18:46_libero_object_swap_t0_s0#seq=12
  - run:20260807-14:18:46_libero_object_swap_t0_s0#seq=24
  - run:20260807-14:18:46_libero_object_swap_t0_s0#seq=28
  - run:20260807-15:01:22_libero_object_swap_t4_s0#seq=36
  - run:20260807-15:21:05_libero_object_swap_t6_s0#seq=63
  - run:20260807-15:21:05_libero_object_swap_t6_s0#seq=93
  - run:20260807-15:52:13_libero_object_swap_t8_s0#seq=30
  - run:20260807-16:08:47_libero_object_swap_t9_s0#seq=39
  counter_evidence: []
- action: endorse
  proposal: logs/gate_gen2/proposals/proposal_03.md
  batch: gate_gen2
  date: '2026-08-08'
  evidence:
  - run:20260807-18:51:17_libero_object_swap_t1_s0#seq=9
  - run:20260807-18:51:17_libero_object_swap_t1_s0#seq=104
  - run:20260807-19:22:13_libero_object_swap_t3_s0#seq=4
  - run:20260807-19:22:13_libero_object_swap_t3_s0#seq=85
  - run:20260807-19:32:33_libero_object_swap_t4_s0#seq=8
  - run:20260807-19:32:33_libero_object_swap_t4_s0#seq=21
  - run:20260807-20:15:39_libero_object_swap_t7_s0#seq=11
  - run:20260807-20:15:39_libero_object_swap_t7_s0#seq=32
  counter_evidence: []
- action: endorse
  proposal: logs/gate_gen3/proposals/proposal_07.md
  batch: gate_gen3
  date: '2026-08-10'
  evidence:
  - run:20260808-11:00:42_libero_object_swap_t0_s0#seq=10
  - run:20260808-11:00:42_libero_object_swap_t0_s0#seq=68
  - run:20260808-12:27:43_libero_object_swap_t7_s0#seq=8
  - run:20260808-12:27:43_libero_object_swap_t7_s0#seq=25
  - run:20260808-12:27:43_libero_object_swap_t7_s0#seq=31
  counter_evidence: []
---

The pi0_pick success flag means the policy call completed, not that the object is in the gripper. Treat every pick as unverified until held-object geometry, origin-box occupancy, and camera re-segmentation agree. If holding is false or the target is still visible on the table, do not begin transport; classify the incident as air-grasp, wander, or push and retry.
---


