---
title: Grasp with pi0 from 6 cm above, then verify geometrically
type: technique
scope: task
conditions: When the stove is on and the moka pot must be lifted.
support: 3
provenance:
- action: add
  proposal: logs/20260814-16:02:54_libero_10_swap_t2_s51/resident_notes.md
  batch: resident_10swap_t2_r2
  date: '2026-08-14'
  evidence:
  - run:20260814-16:02:54_libero_10_swap_t2_s51#seq=32
  - run:20260814-16:02:54_libero_10_swap_t2_s51#seq=9
  - run:20260814-16:02:54_libero_10_swap_t2_s51#seq=10
  counter_evidence: []
---

Pre-position ~6 cm above the measured pot top (split the traversal into
waypoints, |dxy| <= 0.30 each), explicitly set_gripper(-1) to open, then
pi0_pick("pick up the moka pot", max_chunks=35). The grasp is the
stochastic crux: roughly 2/3 of calls close the fingers and only about
half of those lift and hold. Never trust the jaw width or the pick's
return value — verify geometrically before any carry: held_object must
show a cloud below the eef AND the pot's origin box must be empty above
the table (pot airborne). On a full pi0 success it may carry the pot to
the stove itself and termination fires early — accept it.
