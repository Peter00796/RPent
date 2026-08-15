---
title: Pick the bowl with the spatial qualifier, verify by elevation
type: technique
scope: task
conditions: When grasping the black bowl, and whenever pi0_pick reports success.
support: 2
provenance:
- action: add
  proposal: logs/20260815-10:10:41_libero_10_swap_t3_s51/resident_notes.md
  batch: resident_10swap_t3_r1
  date: '2026-08-15'
  evidence:
  - run:20260815-10:10:41_libero_10_swap_t3_s51#seq=10
  - run:20260815-10:10:41_libero_10_swap_t3_s51#seq=33
  counter_evidence: []
---

pi0_pick("pick up the black bowl") air-grasps while NUDGING the bowl
~5 cm and reporting success; the spatial qualifier fixes it: "pick up the
black bowl on the table" (from a pre-position bowl_top + 0.15, gripper
open). Verify geometrically, never by the flag: a fresh agentview "black
bowl" segment must read ELEVATED (z ≈ 0.99-1.04), not at table height.
Destination note: the drawer is the open tray ON THE TABLE — the far-wall
cabinet (x ≈ -1.4) is a distractor; release at the cavity's +y end where
the arm's -y reach wall stalls (that stall is the intended spot).
