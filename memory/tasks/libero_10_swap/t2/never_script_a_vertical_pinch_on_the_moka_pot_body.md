---
title: Never script a vertical pinch on the moka pot body
type: failure_mode
scope: task
conditions: When planning the moka-pot grasp, or after a pi0_pick failure tempts a
  scripted fallback.
support: 8
provenance:
- action: add
  proposal: logs/20260814-16:02:54_libero_10_swap_t2_s51/resident_notes.md
  batch: resident_10swap_t2_r2
  date: '2026-08-14'
  evidence:
  - run:20260814-16:02:54_libero_10_swap_t2_s51#seq=16
  - run:20260814-16:02:54_libero_10_swap_t2_s51#seq=18
  - run:20260814-16:02:54_libero_10_swap_t2_s51#seq=14
  counter_evidence: []
---

The pot is a smooth tapered cylinder (base ~0.078 m, neck ~0.045 m) and the
sim gripper has essentially no friction: a vertical pinch anywhere on the
body or neck pops out under lift load. Seven scripted grasp variations
(jaw 0.040-0.073, including move_pose-threaded pitch) all slipped on the
lift; the single scripted hold that ever survived required an orientation
(~+33 deg pitch, ~+4 deg yaw) that move_to/move_pose cannot reproduce on
demand. Straight-down scripted closes also fail for reach: the fingertips
extend only ~1.3 cm below the eef, so a body-level close is geometrically
out of reach from above. Use the pi0 grasp instead.
