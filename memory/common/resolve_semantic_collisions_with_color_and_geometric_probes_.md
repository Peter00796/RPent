---
title: Resolve semantic collisions with color and geometric probes before committing
  to a target
type: technique
scope: common
conditions: When several object-name prompts land on the same mask; when the scene
  list contains more names than a full enumeration finds; when a second instance is
  being hunted after one complete sweep.
support: 4
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_02.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=2
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=6
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=10
  - run:20260807-15:15:22_libero_object_swap_t5_s0#seq=4
  - run:20260807-15:01:22_libero_object_swap_t4_s0#seq=20
  - run:20260807-16:08:47_libero_object_swap_t9_s0#seq=5
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen3/proposals/proposal_05.md
  batch: gate_gen3
  date: '2026-08-10'
  evidence:
  - run:20260808-11:58:02_libero_object_swap_t5_s0#seq=12
  - run:20260808-11:58:02_libero_object_swap_t5_s0#seq=13
  - run:20260808-11:58:02_libero_object_swap_t5_s0#seq=111
  - run:20260808-11:29:15_libero_object_swap_t2_s0#seq=11
  - run:20260808-11:29:15_libero_object_swap_t2_s0#seq=14
  - run:20260808-11:29:15_libero_object_swap_t2_s0#seq=46
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen4/proposals/proposal_03.md
  batch: gate_gen4
  date: '2026-08-10'
  evidence:
  - run:20260810-17:36:14_libero_object_swap_t1_s0#seq=90
  - run:20260810-17:36:14_libero_object_swap_t1_s0#seq=73
  - run:20260810-18:25:20_libero_object_swap_t5_s0#seq=12
  - run:20260810-18:25:20_libero_object_swap_t5_s0#seq=13
  - run:20260810-18:58:23_libero_object_swap_t8_s0#seq=44
  counter_evidence: []
---

The scene object-name list is not an object-count oracle. When two names collapse onto one mask, that mask is one object unless a second distinct cluster appears. After one complete enumeration, including a lowered z-band when needed, if no extra cluster has appeared, stop hunting; the phantom object does not exist. Resolve the visible instance with wrist/color probes or the pick policy's own language grounding, commit to it, and execute the pick.
