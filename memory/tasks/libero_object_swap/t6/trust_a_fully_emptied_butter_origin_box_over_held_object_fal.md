---
title: Trust a fully emptied butter origin box over held_object=false and image-segmentation
  misses after the pi0 grasp
type: technique
scope: task
conditions: after pi0_pick on the low slab, when deciding whether the butter is actually
  grasped
support: 1
provenance:
- action: add
  proposal: logs/practice_libero_object_swap_t6/round_03/proposals/proposal_01.md
  batch: round_03
  date: '2026-08-11'
  evidence:
  - run:20260811-12:08:54_libero_object_swap_t6_s51#seq=34
  - run:20260811-12:08:54_libero_object_swap_t6_s51#seq=44
  - run:20260811-12:08:54_libero_object_swap_t6_s51#seq=35
  - run:20260811-12:08:54_libero_object_swap_t6_s51#seq=36
  - run:20260811-12:08:54_libero_object_swap_t6_s51#seq=37
  - run:20260811-12:08:54_libero_object_swap_t6_s51#seq=48
  counter_evidence: []
---

After the grasp call, decide “held” by origin-box compare only. If the butter’s origin box goes from occupied to empty (iou 0.0), and a second compare with the arm moved well away from that origin is still empty, treat the slab as grasped. Ignore a held_object=false verdict and wrist/agentview segmentation misses in that situation; they are false negatives caused by the low tool pose. Do not re-grasp, re-scan, or wait for a positive held signal — move directly to the carry.
