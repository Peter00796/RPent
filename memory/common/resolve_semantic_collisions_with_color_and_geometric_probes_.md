---
title: Resolve semantic collisions with color and geometric probes before committing
  to a target
type: technique
scope: common
conditions: Applies when several different object-name prompts land on the same region,
  or when one target name matches multiple distinct regions.
support: 4
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_02.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=2
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=6
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=10
  - run:20260807-15:15:22_libero_object_swap_t5_s0#seq=4
  - run:20260807-15:01:22_libero_object_swap_t4_s0#seq=20
  - run:20260807-16:08:47_libero_object_swap_t9_s0#seq=5
  counter_evidence: []
---

If multiple semantic names collapse onto the same mask, the mask is semantically unreliable. Before picking, separate candidates by color, shape, occupancy, and wrist-camera re-confirmation. If prompts still collide, select the best candidate, act, and let geometric grasp verification arbitrate instead of looping on more names.
---
