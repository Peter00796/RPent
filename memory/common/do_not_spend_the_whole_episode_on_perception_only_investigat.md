---
title: Do not spend the whole episode on perception-only investigation
type: failure_mode
scope: common
conditions: When the target remains ungrounded after a bounded round of name/color/shape
  probes, or after a complete occupancy/back-projection enumeration stops adding candidate
  blobs.
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
---

Replace the generic warning with an actionable cap: the perception phase ends when it stops adding candidates. After one full occupancy/back-projection enumeration, commit to the best-supported candidate and issue the next environment step; if the enumeration isolated one unclaimed cluster, that cluster is the target. Do not re-run failed prompts, re-scan the same windows, or treat the basket as the missing target. A run that never executes a manipulation cannot succeed.
