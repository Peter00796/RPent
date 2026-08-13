---
title: For flat low-profile targets, check gripper closure after pi0_pick; repeated
  empty held_object with unchanged width means air grasp
type: failure_mode
scope: common
conditions: When the target is flat or low-profile; when pi0_pick reports success
  but held_object shows no held body; when the gripper width after repeated attempts
  is essentially unchanged; when geometric and vision readings about the grasp conflict.
support: 2
provenance:
- action: add
  proposal: logs/gate_gen4/proposals/proposal_05.md
  batch: gate_gen4
  date: '2026-08-10'
  evidence:
  - run:20260810-18:35:22_libero_object_swap_t6_s0#seq=58
  - run:20260810-18:35:22_libero_object_swap_t6_s0#seq=59
  - run:20260810-18:35:22_libero_object_swap_t6_s0#seq=69
  - run:20260810-17:36:14_libero_object_swap_t1_s0#seq=95
  - run:20260810-17:36:14_libero_object_swap_t1_s0#seq=96
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen0full_libero_10_swap/proposals/proposal_04.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-17:04:02_libero_10_swap_t6_s0#seq=34
  - run:20260813-17:04:02_libero_10_swap_t6_s0#seq=35
  - run:20260813-17:04:02_libero_10_swap_t6_s0#seq=46
  - run:20260813-17:04:02_libero_10_swap_t6_s0#seq=47
  - run:20260813-17:04:02_libero_10_swap_t6_s0#seq=96
  - run:20260813-18:43:04_libero_10_swap_t7_s0#seq=23
  - run:20260813-18:43:04_libero_10_swap_t7_s0#seq=26
  counter_evidence: []
---

Flat targets are unreliable for pi0: the tool can report success while the fingers close beside the object. When held_object stays empty and the gripper width is essentially unchanged, classify the event as an air grasp immediately. Repeated identical re-picks will not fix it. When geometric sensors and vision conflict, a wrist close-up or a fresh clear-view point segment decides; do not trust the tool success string, the VLM grasp claim, or a contaminated held-object cloud.
