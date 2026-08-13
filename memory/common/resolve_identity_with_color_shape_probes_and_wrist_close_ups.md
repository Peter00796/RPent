---
title: Resolve identity with color/shape probes and wrist close-ups before committing
  a pick
type: technique
scope: common
conditions: When VLM crop reads assign two adjacent candidates the same label or flip
  between them; when a scene read lists objects that geometry cannot confirm.
support: 4
provenance:
- action: add
  proposal: logs/gate_gen2/proposals/proposal_02.md
  batch: gate_gen2
  date: '2026-08-08'
  evidence:
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=10
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=11
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=14
  - run:20260807-19:22:13_libero_object_swap_t3_s0#seq=69
  - run:20260807-19:22:13_libero_object_swap_t3_s0#seq=70
  - run:20260807-19:22:13_libero_object_swap_t3_s0#seq=82
  - run:20260807-18:51:17_libero_object_swap_t1_s0#seq=71
  - run:20260807-19:58:43_libero_object_swap_t6_s0#seq=40
  - run:20260807-19:58:43_libero_object_swap_t6_s0#seq=57
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen0full_libero_object_task/proposals/proposal_02.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-09:29:18_libero_object_task_t0_s0#seq=39
  - run:20260813-09:29:18_libero_object_task_t0_s0#seq=45
  - run:20260813-09:29:18_libero_object_task_t0_s0#seq=46
  - run:20260813-10:02:20_libero_object_task_t2_s0#seq=18
  - run:20260813-10:02:20_libero_object_task_t2_s0#seq=19
  - run:20260813-11:24:22_libero_object_task_t9_s0#seq=13
  counter_evidence: []
---

A single VLM answer is one vote, not identity ground truth. When crop reads flip between adjacent candidates, ask a forced-choice question on larger crops and require agreement with an independent geometric fact: elevated pixels, back-projection height, or an emptied origin box. Back-project any scene-listed candidate before counting it; a phantom candidate with no valid pixels is not evidence of a second instance.
