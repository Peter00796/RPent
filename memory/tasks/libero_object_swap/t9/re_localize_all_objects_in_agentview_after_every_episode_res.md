---
title: Re-localize all objects in agentview after every episode reset
type: invariant
scope: task
conditions: At the start of each attempt, immediately after reset_episode and before
  any manipulation.
support: 1
provenance:
- action: add
  proposal: /mnt/user_dir/pengyanxin/rpent_refactor/logs/resident_libero_object_swap_t9/mine_01_resident/proposals/proposal_01.md
  batch: mine_01_resident
  date: '2026-08-13'
  evidence:
  - run:20260813-00:22:19_libero_object_swap_t9_s51#seq=1
  - run:20260813-00:22:19_libero_object_swap_t9_s51#seq=2
  - run:20260813-00:22:19_libero_object_swap_t9_s51#seq=3
  counter_evidence: []
---

Never trust positions registered to a previous episode. At step 0, segment the orange juice and the basket in agentview and use only those fresh localizations as the basis for every subsequent pick, waypoint, and descent target in the current attempt.
