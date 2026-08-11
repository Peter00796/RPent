---
title: Treat the tomato-sauce/small-red-bottle wrist split as confirmation and pick
  immediately
type: technique
scope: task
conditions: When wrist-hover segmentation probes split so that "brown sauce bottle"
  and "bbq sauce bottle" return false while "tomato sauce bottle" and "small red bottle"
  return true.
support: 1
provenance:
- action: add
  proposal: /mnt/user_dir/pengyanxin/rpent_refactor/logs/resident_libero_object_swap_t5/mine_01_resident/proposals/proposal_02.md
  batch: mine_01_resident
  date: '2026-08-11'
  evidence:
  - run:20260811-15:06:00_libero_object_swap_t5_s51#seq=58
  - run:20260811-15:06:00_libero_object_swap_t5_s51#seq=59
  - run:20260811-15:06:00_libero_object_swap_t5_s51#seq=61
  - run:20260811-15:06:00_libero_object_swap_t5_s51#seq=63
  - run:20260811-15:06:00_libero_object_swap_t5_s51#seq=64
  - run:20260811-15:06:00_libero_object_swap_t5_s51#seq=65
  - run:20260811-15:06:00_libero_object_swap_t5_s51#seq=66
  counter_evidence: []
---

Cross-viewpoint segmentation labels are unstable: at the first hover all four sauce names returned true, but after moving to the second hover the brown and bbq labels became false while "tomato sauce bottle" and "small red bottle" remained true. That split identifies the red bottle as the target. After seeing this split, do not issue another perception call; the failed run ended with a wrist probe right after this confirmed split. Instead, move the EEF to the red bottle, pick it, then place it in the basket.
---
