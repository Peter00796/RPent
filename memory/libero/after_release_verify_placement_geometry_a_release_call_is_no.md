---
curated: gen1b_owner_order 2026-08-14
title: After release, verify placement geometry; a release call is not task success
type: failure_mode
scope: env
conditions: When a release or placement is geometrically confirmed but libero_terminated
  stays false; when the run is considering endless re-verification loops or destructive
  recovery; when two candidate objects are identity-ambiguous.
support: 9
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_09.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-15:01:22_libero_object_swap_t4_s0#seq=63
  - run:20260807-15:01:22_libero_object_swap_t4_s0#seq=66
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=18
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=22
  - run:20260807-15:52:13_libero_object_swap_t8_s0#seq=71
  - run:20260807-15:52:13_libero_object_swap_t8_s0#seq=75
  - run:20260807-16:08:47_libero_object_swap_t9_s0#seq=22
  - run:20260807-16:08:47_libero_object_swap_t9_s0#seq=34
  counter_evidence: []
- action: endorse
  proposal: logs/gate_gen2/proposals/proposal_07.md
  batch: gate_gen2
  date: '2026-08-08'
  evidence:
  - run:20260807-19:32:33_libero_object_swap_t4_s0#seq=6
  - run:20260807-19:32:33_libero_object_swap_t4_s0#seq=29
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=18
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=22
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=43
  - run:20260807-16:08:47_libero_object_swap_t9_s0#seq=23
  - run:20260807-16:08:47_libero_object_swap_t9_s0#seq=33
  counter_evidence: []
- action: endorse
  proposal: logs/gate_gen3/proposals/proposal_10.md
  batch: gate_gen3
  date: '2026-08-10'
  evidence:
  - run:20260808-11:29:15_libero_object_swap_t2_s0#seq=4
  - run:20260808-11:29:15_libero_object_swap_t2_s0#seq=43
  - run:20260808-11:29:15_libero_object_swap_t2_s0#seq=44
  - run:20260808-11:29:15_libero_object_swap_t2_s0#seq=46
  - run:20260808-11:49:24_libero_object_swap_t4_s0#seq=11
  - run:20260808-11:49:24_libero_object_swap_t4_s0#seq=50
  - run:20260808-11:49:24_libero_object_swap_t4_s0#seq=52
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen0full_libero_10_swap/proposals/proposal_10.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-18:43:04_libero_10_swap_t7_s0#seq=59
  - run:20260813-18:43:04_libero_10_swap_t7_s0#seq=85
  - run:20260813-15:52:15_libero_10_swap_t0_s0#seq=90
  - run:20260813-15:52:15_libero_10_swap_t0_s0#seq=91
  - run:20260813-16:37:01_libero_10_swap_t4_s0#seq=78
  - run:20260813-16:37:01_libero_10_swap_t4_s0#seq=79
  counter_evidence: []
---

WHEN: after a release with the flag silent.
RULE: verify from a clear view: right object, inside, seated — not
perched or protruding. If placement verifies correct and the flag is
still silent, keep working (seat it, or re-read the task); silence is
feedback, not permission to conclude.
WHY: rim-perch and wrong-instance placements measured behind silent
flags.
