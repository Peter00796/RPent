---
curated: gen1b_owner_order 2026-08-14
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

WHEN: a VLM answer — identity, state, or pixel — is about to decide an
action.
RULE: it is one vote. Back-project pixel claims and reject any that leave
the support surface. When a VLM verdict conflicts with geometry, geometry
wins: re-measure rather than re-ask.
WHY: measured misfires — pixels at the wrong object's height,
self-contradicting state claims.
