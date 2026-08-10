---
title: Do not spend the whole episode on perception-only investigation
type: failure_mode
scope: common
conditions: When the run has spent many tool calls on segments/back-projections/occupancy
  at an early env step; when the target name repeatedly fails to segment; when a camera-FOV
  exploration move is being considered without an immediate manipulation plan.
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
- action: revise
  proposal: logs/gate_gen5/proposals/proposal_04.md
  batch: gate_gen5
  date: '2026-08-11'
  evidence:
  - run:20260810-20:16:31_libero_object_swap_t3_s0#seq=104
  - run:20260810-20:16:31_libero_object_swap_t3_s0#seq=110
  - run:20260810-21:14:37_libero_object_swap_t8_s0#seq=28
  - run:20260810-21:14:37_libero_object_swap_t8_s0#seq=104
  - run:20260810-21:14:37_libero_object_swap_t8_s0#seq=108
  counter_evidence: []
---

Perception ends after a bounded number of name variants per camera and one complete low-z occupancy enumeration. If the target still has no name, the best-supported unclaimed cluster is the target; execute a pick and verify it geometrically. Moving the wrist to inspect beyond the current view is also perception: if it is not followed by an attempt to manipulate, the episode is lost. A run that never leaves early environment steps, or leaves them only to hover, cannot succeed.
---
