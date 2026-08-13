---
title: VLM scene and state verdicts are not ground truth; decide from geometry
type: invariant
scope: common
conditions: when any VLM answer (pixel box, held/not-held, open/closed, "missing")
  conflicts with occupancy, back-projection, segment relocation, or compare_extent.
support: 4
provenance:
- action: add
  proposal: logs/gate_gen0full_libero_goal_task/proposals/proposal_04.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-09:29:18_libero_goal_task_t0_s0#seq=6
  - run:20260813-09:29:18_libero_goal_task_t0_s0#seq=41
  - run:20260813-09:29:18_libero_goal_task_t0_s0#seq=8
  - run:20260813-10:24:32_libero_goal_task_t2_s0#seq=44
  - run:20260813-10:24:32_libero_goal_task_t2_s0#seq=47
  - run:20260813-10:24:32_libero_goal_task_t2_s0#seq=61
  - run:20260813-10:43:22_libero_goal_task_t3_s0#seq=86
  - run:20260813-10:43:22_libero_goal_task_t3_s0#seq=89
  - run:20260813-10:43:22_libero_goal_task_t3_s0#seq=37
  - run:20260813-10:43:22_libero_goal_task_t3_s0#seq=41
  - run:20260813-10:43:22_libero_goal_task_t3_s0#seq=62
  - run:20260813-11:36:25_libero_goal_task_t7_s0#seq=8
  - run:20260813-11:36:25_libero_goal_task_t7_s0#seq=17
  - run:20260813-11:36:25_libero_goal_task_t7_s0#seq=14
  counter_evidence: []
---

A VLM answer is one vote, not a measurement. When the same VLM changes its answer across calls while occupancy/back-projection geometry stays stable, the geometric reading wins. Do not start a recovery or a verification loop from a VLM "missing", "held", or "open" verdict alone; first check an occupancy box, a handle slot, or a hand-height camera view.
