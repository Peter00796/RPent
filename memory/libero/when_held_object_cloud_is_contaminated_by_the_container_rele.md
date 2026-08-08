---
title: When held-object cloud is contaminated by the container, release from the last
  clean offset
type: technique
scope: env
conditions: At the basket with a held object, when world_extent returns a shape warning
  or a span wider than the gripper can hold.
support: 3
provenance:
- action: add
  proposal: logs/gate_gen2/proposals/proposal_06.md
  batch: gate_gen2
  date: '2026-08-08'
  evidence:
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=47
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=43
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=48
  - run:20260807-19:22:13_libero_object_swap_t3_s0#seq=93
  - run:20260807-19:22:13_libero_object_swap_t3_s0#seq=97
  - run:20260807-19:38:26_libero_object_swap_t5_s0#seq=101
  - run:20260807-19:38:26_libero_object_swap_t5_s0#seq=95
  counter_evidence: []
---

Over or near the basket, the held-object cloud includes points from the container, so its centroid/offset is not the object's offset. Discard that reading. Use the last clean held-object offset recorded in open air plus a fresh basket rim reading to compute the EEF release point. If no clean offset exists, retreat and re-verify the hold before descending.
