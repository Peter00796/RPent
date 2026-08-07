---
title: Do not spend the whole episode on perception-only investigation
type: failure_mode
scope: common
conditions: Applies when the run is repeatedly issuing segmentation, back-projection,
  or occupancy queries without a manipulation command.
support: 3
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_12.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-14:28:32_libero_object_swap_t1_s0#seq=54
  - run:20260807-14:28:32_libero_object_swap_t1_s0#seq=101
  - run:20260807-15:15:22_libero_object_swap_t5_s0#seq=1
  - run:20260807-15:15:22_libero_object_swap_t5_s0#seq=50
  - run:20260807-15:52:13_libero_object_swap_t8_s0#seq=77
  counter_evidence: []
---

Exhaustive scene mapping cannot resolve a language-grounding gap and does not advance the manipulation task. After the first localization pass, commit to the best-supported candidate and issue a pick; let grasp verification arbitrate mistakes. If a vocabulary gap blocks naming, switch to color/shape/occupancy targeting or escalate to the harness instead of continuing to query the same scene.
---
