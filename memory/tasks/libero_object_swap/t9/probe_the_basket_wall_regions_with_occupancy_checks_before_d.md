---
title: Probe the basket wall regions with occupancy checks before descending
type: technique
scope: task
conditions: While carrying the object above the basket, before moving to the descent
  point.
support: 1
provenance:
- action: add
  proposal: /mnt/user_dir/pengyanxin/rpent_refactor/logs/resident_libero_object_swap_t9/mine_01_resident/proposals/proposal_04.md
  batch: mine_01_resident
  date: '2026-08-13'
  evidence:
  - run:20260813-00:22:19_libero_object_swap_t9_s51#seq=9
  - run:20260813-00:22:19_libero_object_swap_t9_s51#seq=10
  - run:20260813-00:22:19_libero_object_swap_t9_s51#seq=11
  - run:20260813-00:22:19_libero_object_swap_t9_s51#seq=12
  - run:20260813-00:22:19_libero_object_swap_t9_s51#seq=13
  counter_evidence: []
---

After carrying above the basket, do not descend immediately. Check that the basket has not moved by querying occupancy over its previously observed wall regions. Only when those probes match the expected basket geometry, move to the descent point computed from the current grasp offset.
