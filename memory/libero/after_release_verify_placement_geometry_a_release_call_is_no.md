---
title: After release, verify placement geometry; a release call is not task success
type: failure_mode
scope: env
conditions: Applies after any release over the basket, especially when the termination
  flag has not fired.
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
---

Release is complete when the gripper opens; task success is a separate condition. If the termination flag stays false, retreat to an unoccluded view, re-segment the object and the basket, and compare the object's extent against the basket opening. If the object is on the rim, outside the opening, or the container has moved, start a repick rather than calling finish.
---


