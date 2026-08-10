---
title: Termination can fire during a closed-gripper descent; do not require a release
type: invariant
scope: env
conditions: When carrying the target over the basket and descending with the gripper
  closed; check the termination flag after every environment step.
support: 6
provenance:
- action: add
  proposal: logs/gate_gen3/proposals/proposal_03.md
  batch: gate_gen3
  date: '2026-08-10'
  evidence:
  - run:20260808-11:37:47_libero_object_swap_t3_s0#seq=90
  - run:20260808-11:37:47_libero_object_swap_t3_s0#seq=91
  - run:20260808-11:37:47_libero_object_swap_t3_s0#seq=93
  - run:20260808-11:49:24_libero_object_swap_t4_s0#seq=49
  - run:20260808-11:49:24_libero_object_swap_t4_s0#seq=52
  - run:20260808-12:27:43_libero_object_swap_t7_s0#seq=36
  - run:20260808-12:27:43_libero_object_swap_t7_s0#seq=40
  counter_evidence: []
- action: endorse
  proposal: logs/gate_gen4/proposals/proposal_07.md
  batch: gate_gen4
  date: '2026-08-10'
  evidence:
  - run:20260810-18:51:12_libero_object_swap_t7_s0#seq=46
  - run:20260810-18:51:12_libero_object_swap_t7_s0#seq=47
  - run:20260810-18:58:23_libero_object_swap_t8_s0#seq=62
  - run:20260810-19:07:57_libero_object_swap_t9_s0#seq=54
  counter_evidence: []
---

In this environment, the success predicate may evaluate true while the gripper is still closed during the final descent into the basket; it does not wait for a release. After any descent that enters the basket, read the termination flag. If it is true, run the interior geometry check, write the audit, and call finish. Do not keep stepping until a release appears, and do not call release merely to advance the state.

