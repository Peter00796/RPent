---
title: Release into hollow interiors for slatted fixtures rather than only on their
  top
type: technique
scope: common
conditions: When the placement fixture is a slatted or hollow structure (rack, shelf,
  open crate); when a top-surface release fails to satisfy the checker.
support: 1
provenance:
- action: add
  proposal: logs/gate_gen0full_libero_goal_swap/proposals/proposal_11.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-14:03:19_libero_goal_swap_t9_s0#seq=72
  - run:20260813-14:03:19_libero_goal_swap_t9_s0#seq=82
  - run:20260813-14:03:19_libero_goal_swap_t9_s0#step=32
  counter_evidence: []
---

For a slatted/hollow fixture (rack, shelf, open crate), the placement target may be the interior, not the top surface. Probe the top rim and interior floor heights, check the wrist view for openings, and prefer releasing inside the hollow when the checker does not fire on the top. A top release can sink between slats without satisfying the predicate.
