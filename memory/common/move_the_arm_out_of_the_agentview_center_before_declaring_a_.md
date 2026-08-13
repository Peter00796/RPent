---
title: Move the arm out of the agentview center before declaring a target absent from
  the scene
type: technique
scope: common
conditions: When an agentview crop or scene read cannot find the target and the arm
  occupies the central view of the camera.
support: 1
provenance:
- action: add
  proposal: logs/gate_gen0full_libero_object_task/proposals/proposal_09.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-10:22:41_libero_object_task_t4_s0#seq=20
  - run:20260813-10:22:41_libero_object_task_t4_s0#seq=21
  - run:20260813-10:22:41_libero_object_task_t4_s0#seq=22
  - run:20260813-10:22:41_libero_object_task_t4_s0#seq=23
  counter_evidence: []
---

The arm itself can occlude the only instance of the target from agentview. Before exhausting name prompts or declaring the object absent, move the arm to a position outside the central view and re-survey the scene. One deliberate re-positioning is justified when it is immediately followed by re-localization and a manipulation plan; it is not a license for unbounded camera exploration.
