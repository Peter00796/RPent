---
title: Verify every pi0 pick with held-object extent and origin-box comparison
type: technique
scope: task
conditions: After each pi0_pick attempt and before carrying the object.
support: 1
provenance:
- action: add
  proposal: /mnt/user_dir/pengyanxin/rpent_refactor/logs/resident_libero_object_swap_t9/mine_01_resident/proposals/proposal_02.md
  batch: mine_01_resident
  date: '2026-08-13'
  evidence:
  - run:20260813-00:22:19_libero_object_swap_t9_s51#seq=5
  - run:20260813-00:22:19_libero_object_swap_t9_s51#seq=6
  - run:20260813-00:22:19_libero_object_swap_t9_s51#seq=7
  counter_evidence: []
---

Do not accept pi0_pick success alone. After the pick, confirm the grasp by measuring the held-object extent and comparing the object’s origin box before/after the pick. Only proceed to carry once both geometric checks indicate the object is actually in the gripper.
