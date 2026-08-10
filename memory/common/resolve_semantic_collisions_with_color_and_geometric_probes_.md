---
title: Resolve semantic collisions with color and geometric probes before committing
  to a target
type: technique
scope: common
conditions: When several object-name prompts land on the same mask, when color/name
  probes keep returning the same region, or when the object list implies an extra
  instance that a full table enumeration never finds.
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
---

If several semantic names collapse onto one mask, the mask is not evidence of multiple objects. Do not infer a hidden second instance just because the scene list has two names. Identify the visible instance with discriminating prompts (single-word label, color/shape, wrist close-up) and commit to it. Bound the search for a second instance by one full occupancy/back-projection enumeration; if no second mask appears, proceed with the instance you have.
