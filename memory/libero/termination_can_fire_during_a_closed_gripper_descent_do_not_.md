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
- action: revise
  proposal: logs/fix_5f_proposals/p1.md
  batch: fix_5f
  date: '2026-08-12'
  evidence:
  - run:20260812-12:06:23_libero_object_swap_t5_s0#seq=62
  - run:20260812-14:15:31_libero_object_swap_t5_s0#seq=38
  - run:20260812-12:56:23_libero_object_swap_t9_s0#seq=46
  counter_evidence: []
---

Keep the existing fact that termination can fire during a closed-gripper
descent and that a release call is not required, and keep the requirement of
at least two independent physical checks (origin box emptied, held/table
absence, basket-interior occupancy, or a lowered wrist view). REPLACE the
old closing licence ("treat the task as complete"): if the checks pass and
termination has STILL not fired, you have a CONTRADICTION between your own
verification and the environment's scoring authority — and the flag is the
authority. Presence checks cannot detect a wrong-object placement: putting
the WRONG object in the basket passes every one of them while the checker
rightly stays silent. Before stopping, verify the IDENTITY of the object
actually inside the basket (read its label via the vision channel if armed,
or match its measured geometry against the target's signature) — not merely
that something you placed is present. If the identity check fails, treat the
run as a wrong-object failure and recover. Only if the verified TARGET is
inside and the flag is still silent may checker flakiness be considered:
record the contradiction explicitly in the audit and finish with an honest
status describing it — never an unqualified success. Do not keep re-seating
the object with closed-gripper descents in either case.

Gen-0 full-benchmark additions (batch gen0full_night, manual merge; evidence: run:20260813 object_swap/goal sweeps): the flag also will NOT fire while the placed object still protrudes above the container rim — a non-firing flag with a protruding object is a seating problem, not checker flakiness. And a fire DURING a closed-gripper descent or before the arm retreats still counts: the episode is over the moment it fires; do not issue further motions after it.
