---
title: For flat low-profile targets, check gripper closure after pi0_pick; repeated
  empty held_object with unchanged width means air grasp
type: failure_mode
scope: common
conditions: When the target is a flat low-profile slab; when pi0_pick reports success
  but held_object stays empty; when the reported gripper width is essentially unchanged
  across repeated empty held-object readings at about 0.039 m.
support: 2
provenance:
- action: add
  proposal: logs/gate_gen4/proposals/proposal_05.md
  batch: gate_gen4
  date: '2026-08-10'
  evidence:
  - run:20260810-18:35:22_libero_object_swap_t6_s0#seq=58
  - run:20260810-18:35:22_libero_object_swap_t6_s0#seq=59
  - run:20260810-18:35:22_libero_object_swap_t6_s0#seq=69
  - run:20260810-17:36:14_libero_object_swap_t1_s0#seq=95
  - run:20260810-17:36:14_libero_object_swap_t1_s0#seq=96
  counter_evidence: []
---

Flat slabs are unreliable pi0 targets: the pick can close with the fingers beside the slab without pinching it. When held_object is empty and the reported gripper width is essentially unchanged from the pre-pick width, classify the event as an air grasp immediately; do not keep re-probing the same grasp. Re-localize the slab and attempt a different approach, such as re-posing the object, an edge-on pick, or a scripted grasp with contact verification. A single empty reading is not decisive, but a constant gripper width across repeated empty readings marks the miss.
