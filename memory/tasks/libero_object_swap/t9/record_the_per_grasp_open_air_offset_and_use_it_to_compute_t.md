---
title: Record the per-grasp open-air offset and use it to compute the descent target
type: technique
scope: task
conditions: After a verified pick and before computing the basket descent point.
support: 1
provenance:
- action: add
  proposal: /mnt/user_dir/pengyanxin/rpent_refactor/logs/resident_libero_object_swap_t9/mine_01_resident/proposals/proposal_03.md
  batch: mine_01_resident
  date: '2026-08-13'
  evidence:
  - run:20260813-00:22:19_libero_object_swap_t9_s51#seq=6
  - run:20260813-00:22:19_libero_object_swap_t9_s51#seq=13
  - run:20260813-00:22:19_libero_object_swap_t9_s51#seq=18
  counter_evidence: []
---

While holding the object cleanly in open air, capture the logged EEF offset from the held-object measurement. This offset is per grasp and changes between attempts, so never reuse a previous solve’s offset. Compute the descent EEF x/y as the basket rim-centre x/y minus the current attempt’s offset; the successful run used exactly this relationship for the final descent.
