---
title: Do not spend the whole episode on perception-only investigation
type: failure_mode
scope: common
conditions: When all tool calls so far are reads, segments, back-projections, or occupancy
  queries at environment step 0; when a lowered z-band sweep has completed without
  adding a new cluster; when the run is about to re-scan a region it already enumerated.
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
- action: revise
  proposal: logs/gate_gen3/proposals/proposal_02.md
  batch: gate_gen3
  date: '2026-08-10'
  evidence:
  - run:20260808-11:58:02_libero_object_swap_t5_s0#seq=111
  - run:20260808-12:13:27_libero_object_swap_t6_s0#seq=108
  - run:20260808-12:13:27_libero_object_swap_t6_s0#seq=110
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen4/proposals/proposal_01.md
  batch: gate_gen4
  date: '2026-08-10'
  evidence:
  - run:20260810-18:25:20_libero_object_swap_t5_s0#seq=74
  - run:20260810-17:21:40_libero_object_swap_t0_s0#seq=72
  - run:20260810-17:36:14_libero_object_swap_t1_s0#seq=81
  counter_evidence: []
---

Perception ends when one full occupancy/back-projection enumeration, including the lowered z-band when warranted, stops producing new candidate clusters. After that, no further probing or re-wording is admission-worthy; commit to the best-supported candidate and execute an environment step. If the semantic list implies more objects than clusters, treat it as a label collision, not a license to keep scanning. A run that never leaves step 0 cannot succeed.
