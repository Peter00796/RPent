---
title: Do not spend the whole episode on perception-only investigation
type: failure_mode
scope: common
conditions: When the target is not grounded after a small number of probes, or after
  several segmentation/back-project calls return no new candidates.
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
- action: revise
  proposal: logs/gate_gen2/proposals/proposal_08.md
  batch: gate_gen2
  date: '2026-08-08'
  evidence:
  - run:20260807-19:58:43_libero_object_swap_t6_s0#seq=55
  - run:20260807-19:58:43_libero_object_swap_t6_s0#seq=62
  - run:20260807-14:28:32_libero_object_swap_t1_s0#seq=2
  - run:20260807-14:28:32_libero_object_swap_t1_s0#seq=4
  - run:20260807-15:15:22_libero_object_swap_t5_s0#seq=50
  counter_evidence: []
---

Replace the vague warning with an actionable cap: after a bounded number of segmentation/back-project probes that do not add new candidate or identity information, stop re-probing and either (a) switch to color/shape and wrist close-up probes, (b) run a full occupancy enumeration of the table, or (c) commit to the best candidate and take the first env step. Do not re-run the same failed prompt on the same frame.
