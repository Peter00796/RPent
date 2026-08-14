---
curated: gen1b_owner_order 2026-08-14
title: Re-localize the basket after every carry; identity_warning means movement,
  not noise
type: technique
scope: env
conditions: After any pick, before any carry/release; when the basket was last segmented
  at step 0; when the arm has moved and the previous basket anchor may be stale.
support: 11
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_07.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-14:44:02_libero_object_swap_t2_s0#seq=13
  - run:20260807-14:44:02_libero_object_swap_t2_s0#seq=36
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=23
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=25
  - run:20260807-16:08:47_libero_object_swap_t9_s0#seq=18
  - run:20260807-16:08:47_libero_object_swap_t9_s0#seq=36
  counter_evidence: []
- action: endorse
  proposal: logs/gate_gen2/proposals/proposal_05.md
  batch: gate_gen2
  date: '2026-08-08'
  evidence:
  - run:20260807-19:32:33_libero_object_swap_t4_s0#seq=5
  - run:20260807-19:32:33_libero_object_swap_t4_s0#seq=26
  - run:20260807-20:15:39_libero_object_swap_t7_s0#seq=6
  - run:20260807-20:15:39_libero_object_swap_t7_s0#seq=38
  - run:20260807-19:22:13_libero_object_swap_t3_s0#seq=8
  - run:20260807-19:22:13_libero_object_swap_t3_s0#seq=88
  - run:20260807-16:08:47_libero_object_swap_t9_s0#seq=18
  - run:20260807-16:08:47_libero_object_swap_t9_s0#seq=36
  counter_evidence: []
- action: endorse
  proposal: logs/gate_gen3/proposals/proposal_08.md
  batch: gate_gen3
  date: '2026-08-10'
  evidence:
  - run:20260808-11:29:15_libero_object_swap_t2_s0#seq=6
  - run:20260808-11:29:15_libero_object_swap_t2_s0#seq=34
  - run:20260808-11:29:15_libero_object_swap_t2_s0#seq=40
  - run:20260808-12:27:43_libero_object_swap_t7_s0#seq=4
  - run:20260808-12:27:43_libero_object_swap_t7_s0#seq=34
  - run:20260808-12:27:43_libero_object_swap_t7_s0#seq=40
  counter_evidence: []
- action: endorse
  proposal: logs/gate_gen4/proposals/proposal_08.md
  batch: gate_gen4
  date: '2026-08-10'
  evidence:
  - run:20260810-17:51:34_libero_object_swap_t2_s0#seq=7
  - run:20260810-17:51:34_libero_object_swap_t2_s0#seq=26
  - run:20260810-17:51:34_libero_object_swap_t2_s0#seq=31
  - run:20260810-19:07:57_libero_object_swap_t9_s0#seq=50
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen0full_libero_object_swap/proposals/proposal_12.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-12:05:21_libero_object_swap_t1_s0#seq=3
  - run:20260813-12:05:21_libero_object_swap_t1_s0#seq=33
  - run:20260813-12:11:38_libero_object_swap_t3_s0#seq=23
  - run:20260813-12:10:54_libero_object_swap_t4_s0#seq=22
  - run:20260813-12:26:26_libero_object_swap_t7_s0#seq=13
  counter_evidence: []
---

WHEN: before the carry and before the release.
RULE: re-segment the destination after the pick — any anchor from step 0
is stale once the arm has moved. Aim at the fresh opening centre, never
the stored interior median.
WHY: stale anchors measured to produce rim-stall releases.
