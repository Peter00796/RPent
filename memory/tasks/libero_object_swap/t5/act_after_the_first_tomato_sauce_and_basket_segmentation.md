---
title: Act after the first tomato-sauce and basket segmentation
type: technique
scope: task
conditions: When the tomato-sauce mask and basket mask are known and a pi0_pick has
  just been issued for the tomato-sauce bottle.
support: 2
provenance:
- action: add
  proposal: /mnt/user_dir/pengyanxin/rpent_refactor/logs/resident_libero_object_swap_t5/mine_00_old/proposals/proposal_01.md
  batch: mine_00_old
  date: '2026-08-11'
  evidence:
  - run:20260811-05:33:43_libero_object_swap_t5_s51#seq=10
  - run:20260811-05:33:43_libero_object_swap_t5_s51#seq=14
  - run:20260811-05:33:43_libero_object_swap_t5_s51#seq=15
  - run:20260811-06:29:45_libero_object_swap_t5_s53#seq=48
  counter_evidence: []
- action: revise
  proposal: logs/resident_libero_object_swap_t5/mine_02_vision/proposals/proposal_01.md
  batch: resident_mine_02
  date: '2026-08-11'
  evidence:
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=5
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=6
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=11
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=27
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=28
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=30
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=31
  counter_evidence: []
---

Proceed to move -> grasp -> verify -> move -> place. The pick primitive's success return is not evidence that the bottle is in the gripper: in this run the first pick reported success while the bottle remained on the floor, and a second pick from a close pre-position with the "small red bottle" prompt also failed to show a verified held-object cloud after lift. After every pick, call held_object and require a cloud below the eef before carrying the bottle to the basket. A zero-point result with the gripper closed is ambiguous with occlusion, so move the wrist to a clear viewpoint and re-check before treating the pick as failed.
