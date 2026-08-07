---
title: When target-name segmentation fails, retry with color/shape prompts before
  declaring the object absent
type: technique
scope: common
conditions: Applies when a text-prompt segmentation for the task object returns found=false,
  or when the only successful prompts are weak or mismatched.
support: 3
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_01.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-14:18:46_libero_object_swap_t0_s0#seq=3
  - run:20260807-14:18:46_libero_object_swap_t0_s0#seq=5
  - run:20260807-15:52:13_libero_object_swap_t8_s0#seq=17
  - run:20260807-15:52:13_libero_object_swap_t8_s0#seq=20
  - run:20260807-15:21:05_libero_object_swap_t6_s0#seq=35
  counter_evidence:
  - run:20260807-14:28:32_libero_object_swap_t1_s0#seq=2
---

Admit each segmentation result as one vote, not ground truth. When the target-name prompt returns false, retry with color and shape phrasings; a successful color/shape prompt gives a usable working target. If every variant fails, do not keep expanding the naming loop; commit to the best-supported hypothesis or escalate the vocabulary gap to the harness.
---
