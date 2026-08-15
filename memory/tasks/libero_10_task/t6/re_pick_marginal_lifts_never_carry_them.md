---
title: Re-pick marginal lifts — never carry them
type: failure_mode
scope: task
conditions: Immediately after any pi0 pick of the mug or pudding, before any carry.
support: 2
provenance:
- action: add
  proposal: logs/20260815-10:42:41_libero_10_task_t6_s51/resident_notes.md
  batch: resident_10task_t6_r1
  date: '2026-08-15'
  evidence:
  - run:20260815-10:42:41_libero_10_task_t6_s51#seq=12
  counter_evidence: []
---

A marginal grasp (held_object centroid still near table level, lift
< 2 cm) dragged the mug across the table when carried. The gate is
strict: require the held cloud's centroid z > 0.48 (clearly airborne)
before any lateral motion; otherwise open the gripper in place and
re-pick from a fresh pre-position.
