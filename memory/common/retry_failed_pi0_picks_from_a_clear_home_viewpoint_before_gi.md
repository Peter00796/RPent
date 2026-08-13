---
title: Retry failed Pi0 picks from a clear/home viewpoint before giving up
type: technique
scope: common
conditions: after a pi0_pick reports success but nothing is held; after a pick whose
  hold is not confirmed geometrically; when the target is flat or lying and the generic
  pick prompt has already failed.
support: 1
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_05.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=28
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=33
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=43
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=44
  counter_evidence:
  - run:20260807-16:08:47_libero_object_swap_t9_s0#seq=59
- action: revise
  proposal: logs/gate_gen3/proposals/proposal_04.md
  batch: gate_gen3
  date: '2026-08-10'
  evidence:
  - run:20260808-11:00:42_libero_object_swap_t0_s0#seq=68
  - run:20260808-11:00:42_libero_object_swap_t0_s0#seq=71
  - run:20260808-11:00:42_libero_object_swap_t0_s0#seq=77
  - run:20260808-11:00:42_libero_object_swap_t0_s0#seq=78
  - run:20260808-12:47:32_libero_object_swap_t9_s0#seq=34
  - run:20260808-12:47:32_libero_object_swap_t9_s0#seq=47
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen4/proposals/proposal_04.md
  batch: gate_gen4
  date: '2026-08-10'
  evidence:
  - run:20260810-17:57:07_libero_object_swap_t3_s0#seq=85
  - run:20260810-17:57:07_libero_object_swap_t3_s0#seq=87
  - run:20260810-17:57:07_libero_object_swap_t3_s0#seq=92
  - run:20260810-17:57:07_libero_object_swap_t3_s0#step=12
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen5/proposals/proposal_03.md
  batch: gate_gen5
  date: '2026-08-11'
  evidence:
  - run:20260810-20:52:58_libero_object_swap_t6_s0#seq=87
  - run:20260810-20:52:58_libero_object_swap_t6_s0#seq=93
  - run:20260810-20:52:58_libero_object_swap_t6_s0#seq=94
  - run:20260810-20:52:58_libero_object_swap_t6_s0#seq=102
  - run:20260810-20:52:58_libero_object_swap_t6_s0#seq=112
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen0full_libero_goal_task/proposals/proposal_01.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-10:14:39_libero_goal_task_t1_s0#seq=15
  - run:20260813-10:14:39_libero_goal_task_t1_s0#seq=19
  - run:20260813-10:14:39_libero_goal_task_t1_s0#seq=20
  - run:20260813-10:43:22_libero_goal_task_t3_s0#seq=78
  - run:20260813-10:43:22_libero_goal_task_t3_s0#seq=95
  - run:20260813-11:07:52_libero_goal_task_t4_s0#seq=18
  - run:20260813-11:07:52_libero_goal_task_t4_s0#seq=32
  - run:20260813-11:28:48_libero_goal_task_t6_s0#seq=18
  - run:20260813-11:45:08_libero_goal_task_t8_s0#seq=27
  - run:20260813-10:24:32_libero_goal_task_t2_s0#seq=30
  counter_evidence:
  - run:20260813-11:07:52_libero_goal_task_t4_s0#seq=21
---

A pi0_pick "success" is not a completed grasp. Do not repeat the same pick from the same stale pre-position: failed attempts can nudge a table object, so re-measure its footprint from a clean view before retrying. The retry should be launched from home or from a fresh pre-position over the re-measured center; returning home with an unchanged prompt is not enough. For flat or lying targets, add a spatial qualifier to the pick prompt (e.g. "lying on the table", "on the table"). Verify the retry by gripper width matching the target and by a hand-height camera view before transport.
