---
title: Re-localize the basket after every carry; identity_warning means movement,
  not noise
type: technique
scope: env
conditions: Applies while carrying the target toward the basket, after any stalled
  move, or when a re-segmentation returns an identity_warning.
support: 7
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
---

The basket is an unanchored object and can be bumped by the arm or by a stalled move. A segmentation identity_warning or a changed rim reading is a displacement signal, not sensor noise. Re-localize the container and re-check occupancy before computing the release target; never reuse the step-0 basket mask for a later placement.
---

