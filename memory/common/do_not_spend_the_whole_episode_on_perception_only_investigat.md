---
title: Do not spend the whole episode on perception-only investigation
type: failure_mode
scope: common
conditions: When the run has made many perception calls but no manipulation env-step;
  when it is still at step 0 or step 1; when each perception call is followed by another
  perception call rather than a pick/place attempt.
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
- action: revise
  proposal: logs/gate_gen0full_libero_10_swap/proposals/proposal_07.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-17:02:11_libero_10_swap_t1_s0#seq=1
  - run:20260813-17:02:11_libero_10_swap_t1_s0#seq=120
  - run:20260813-18:08:26_libero_10_swap_t5_s0#seq=71
  - run:20260813-18:08:26_libero_10_swap_t5_s0#seq=115
  counter_evidence: []
---

A run that never leaves the early environment steps cannot succeed. Set a hard budget: a bounded set of name variants per camera, one wrist pass, one low-z occupancy enumeration. After the budget is exhausted, act on the best candidate and verify the result geometrically. Moving the arm to inspect a new viewpoint is still perception; if it is not followed by a manipulation attempt, the episode is lost.
