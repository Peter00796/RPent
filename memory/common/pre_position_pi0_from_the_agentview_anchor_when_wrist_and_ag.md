---
title: Pre-position pi0 from the agentview anchor when wrist and agentview disagree
type: technique
scope: common
conditions: Applies when a pi0 pick missed and the diagnosis shows an offset between
  the wrist-camera footprint center and the agentview footprint center.
support: 1
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_04.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-14:18:46_libero_object_swap_t0_s0#seq=24
  - run:20260807-14:18:46_libero_object_swap_t0_s0#seq=27
  - run:20260807-14:18:46_libero_object_swap_t0_s0#seq=31
  - run:20260807-14:18:46_libero_object_swap_t0_s0#seq=33
  counter_evidence: []
---

When a pick closes on air, compare the camera anchors. A wrist-camera footprint can lead the EEF to a point offset from the true grasp point. Reissue the pick with the pre-pose taken from the agentview center, then verify by held-object geometry and gripper contact rather than by tool status.
---
