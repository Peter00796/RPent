---
title: Termination can fire during a closed-gripper descent; do not require a release
type: invariant
scope: env
conditions: When an environment termination fires while the gripper is closed or during
  a pick/descent; when a run is waiting for termination to decide whether placement
  succeeded.
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
- action: revise
  proposal: logs/gate_gen5/proposals/proposal_02.md
  batch: gate_gen5
  date: '2026-08-11'
  evidence:
  - run:20260810-21:45:48_libero_object_swap_t0_s0#seq=7
  - run:20260810-21:45:48_libero_object_swap_t0_s0#seq=8
  - run:20260810-21:45:48_libero_object_swap_t0_s0#seq=12
  - run:20260810-21:45:48_libero_object_swap_t0_s0#seq=13
  - run:20260810-20:31:41_libero_object_swap_t4_s0#seq=61
  - run:20260810-20:31:41_libero_object_swap_t4_s0#seq=62
  - run:20260810-20:46:39_libero_object_swap_t5_s0#seq=34
  - run:20260810-20:46:39_libero_object_swap_t5_s0#seq=36
  counter_evidence: []
---

Keep the existing fact that termination can fire during a closed-gripper descent and that a release call is not required. Extend it: termination is a signal to verify, not an oracle. It can fire while nothing is grasped and the target is still on the table; it can also fail to fire when the object is already inside the basket. Before declaring success, require at least two independent physical checks (origin box emptied, held/table absence, basket-interior occupancy, or a lowered wrist view). If the object is confirmed inside the basket and the origin is empty but termination has not fired, treat the task as complete; do not keep re-seating the object with closed-gripper descents.
---
