---
title: Spread-grasp the bowl from inside — the jaw cannot pinch it
type: technique
scope: task
conditions: When the black bowl must be lifted and no VLA pick is available (or it
  has failed) — plan_grasp reports no feasible antipodal span on the Ø0.11 body.
support: 2
provenance:
- action: add
  proposal: logs/20260815-23:44:15_libero_10_swap_t3_s51/resident_notes.md
  batch: plangrasp_sw3_r1
  date: '2026-08-16'
  evidence:
  - run:20260815-23:44:15_libero_10_swap_t3_s51#seq=45
  - run:20260815-23:44:15_libero_10_swap_t3_s51#seq=49
  counter_evidence: []
---

The Ø0.11 bowl exceeds the 0.072 jaw — plan_grasp's no_feasible verdict
on the body is correct and stable; do not re-query it. The working grasp
is a SPREAD from inside: hover over the rim center, descend with the
gripper OPEN to rim + 0.006, then continue to rim − 0.025 so the open
fingers enter the bowl and WEDGE against the inner walls (descent stalls
at eef z ~0.93; qpos compresses ~0.039 → 0.030 from wall pressure), then
lift with the gripper still open — the bowl rides up on the spread
fingers. Verify: a fresh bowl segment reads elevated at eef height.
Keep the spread through the whole carry; releasing the spread is the
place action.
