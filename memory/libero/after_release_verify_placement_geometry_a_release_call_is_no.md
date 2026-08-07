---
title: After release, verify placement geometry; a release call is not task success
type: failure_mode
scope: env
conditions: Applies after any release over the basket, especially when the termination
  flag has not fired.
support: 4
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
---

Release is complete when the gripper opens; task success is a separate condition. If the termination flag stays false, retreat to an unoccluded view, re-segment the object and the basket, and compare the object's extent against the basket opening. If the object is on the rim, outside the opening, or the container has moved, start a repick rather than calling finish.
---
