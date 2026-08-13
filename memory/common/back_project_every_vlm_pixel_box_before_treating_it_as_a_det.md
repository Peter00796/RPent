---
title: Back-project every VLM pixel box before treating it as a detection
type: failure_mode
scope: common
conditions: When a VLM inspect/image answer reports an object center, bounding box,
  or pixel region; before using that pixel for a point-prompt, grasp, or release;
  when a VLM pixel conflicts with an existing mask.
support: 4
provenance:
- action: add
  proposal: logs/gate_gen0full_libero_10_task/proposals/proposal_02.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-14:25:19_libero_10_task_t4_s0#seq=8
  - run:20260813-14:25:19_libero_10_task_t4_s0#seq=10
  - run:20260813-14:25:19_libero_10_task_t4_s0#seq=15
  - run:20260813-14:33:16_libero_10_task_t1_s0#seq=11
  - run:20260813-14:33:16_libero_10_task_t1_s0#seq=14
  - run:20260813-14:02:23_libero_10_task_t0_s0#seq=23
  - run:20260813-16:25:58_libero_10_task_t9_s0#seq=42
  - run:20260813-16:25:58_libero_10_task_t9_s0#seq=47
  counter_evidence: []
---

VLM pixel outputs are hypotheses, not detections. Before a VLM-reported region seeds a point-prompt, grasp, or release, back-project it into the occupancy map. Reject any region that resolves to the table/background, conflicts with another object at the same pixel, or returns a constant floor value; these patterns appeared for dark, flat, and handle-sized objects. Only a region whose back-projection shows object-height geometry may be used as a working location.
