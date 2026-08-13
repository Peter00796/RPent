---
title: Re-measure the held-object offset before computing the release target
type: technique
scope: common
conditions: After pick verification; during transport; before the final descent and
  release; when a carry waypoint was already planned from an earlier offset.
support: 8
provenance:
- action: add
  proposal: logs/gate_gen0full_libero_spatial_swap/proposals/proposal_03.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-13:37:14_libero_spatial_swap_t0_s0#seq=27
  - run:20260813-13:37:14_libero_spatial_swap_t0_s0#seq=30
  - run:20260813-13:40:37_libero_spatial_swap_t1_s0#seq=29
  - run:20260813-13:40:37_libero_spatial_swap_t1_s0#seq=33
  - run:20260813-13:43:25_libero_spatial_swap_t2_s0#seq=18
  - run:20260813-13:48:03_libero_spatial_swap_t3_s0#seq=65
  - run:20260813-13:49:21_libero_spatial_swap_t4_s0#seq=41
  - run:20260813-14:03:26_libero_spatial_swap_t5_s0#seq=36
  - run:20260813-14:45:02_libero_spatial_swap_t8_s0#seq=49
  - run:20260813-14:19:38_libero_spatial_swap_t9_s0#seq=26
  counter_evidence: []
---

Do not carry the post-grasp offset all the way to the release. After pick verification, measure a clean held-object offset in open air. Once the end effector is above the destination, re-measure the offset and re-segment the destination center. If the offset changed, recompute the final xy so that the object, not the end effector, is centered over the destination; then descend and release.
---
