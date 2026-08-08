---
title: A single held-object reading is not decisive; require convergent evidence
type: failure_mode
scope: common
conditions: After a pick, during transport, or when held-object reports contradictory
  states.
support: 4
provenance:
- action: add
  proposal: logs/gate_gen2/proposals/proposal_04.md
  batch: gate_gen2
  date: '2026-08-08'
  evidence:
  - run:20260807-15:01:22_libero_object_swap_t4_s0#seq=38
  - run:20260807-15:01:22_libero_object_swap_t4_s0#seq=45
  - run:20260807-18:51:17_libero_object_swap_t1_s0#seq=103
  - run:20260807-18:51:17_libero_object_swap_t1_s0#seq=109
  - run:20260807-15:52:13_libero_object_swap_t8_s0#seq=45
  - run:20260807-15:52:13_libero_object_swap_t8_s0#seq=48
  - run:20260807-20:22:07_libero_object_swap_t8_s0#seq=58
  - run:20260807-20:22:07_libero_object_swap_t8_s0#seq=61
  counter_evidence: []
---

`held_object=true` can follow a push that displaced the object without grasping it, and `held_object=false`/0 points can follow a successful grasp when the object is occluded or outside the queried volume. Do not trust one reading. Confirm with at least one independent signal: origin-box voxel removal, wrist close-up occupancy, or camera re-segmentation of an elevated object. If readings conflict, retreat to a clear viewpoint, re-localize, and re-check before any release.
