---
title: Retry failed Pi0 picks from a clear/home viewpoint before giving up
type: technique
scope: common
conditions: After any pi0_pick whose held-object verification reports no object, or
  an air grasp diagnosed after lifting, as well as after repeated close-range failures.
support: 1
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_05.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=28
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=33
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=43
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=44
  counter_evidence:
  - run:20260807-16:08:47_libero_object_swap_t9_s0#seq=59
- action: revise
  proposal: logs/gate_gen3/proposals/proposal_04.md
  batch: gate_gen3
  date: '2026-08-10'
  evidence:
  - run:20260808-11:00:42_libero_object_swap_t0_s0#seq=68
  - run:20260808-11:00:42_libero_object_swap_t0_s0#seq=71
  - run:20260808-11:00:42_libero_object_swap_t0_s0#seq=77
  - run:20260808-11:00:42_libero_object_swap_t0_s0#seq=78
  - run:20260808-12:47:32_libero_object_swap_t9_s0#seq=34
  - run:20260808-12:47:32_libero_object_swap_t9_s0#seq=47
  counter_evidence: []
---

A pick is unverified until geometry says otherwise. If the first verification contradicts the pick, do not re-issue the pick from the same close stance; the object may have been nudged. Retreat to neutral, re-localize from an unoccluded view, return to a clear/home pose, and issue a fresh pi0_pick from there. Verify the retry with the same held-object check before transport.
