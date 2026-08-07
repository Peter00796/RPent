---
title: Verify every pi0 pick geometrically before transport
type: failure_mode
scope: common
conditions: Applies after any pi0_pick call, regardless of the tool-reported success
  status.
support: 5
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
---

The pi0_pick success flag means the policy call completed, not that the object is in the gripper. Treat every pick as unverified until held-object geometry, origin-box occupancy, and camera re-segmentation agree. If holding is false or the target is still visible on the table, do not begin transport; classify the incident as air-grasp, wander, or push and retry.
---
