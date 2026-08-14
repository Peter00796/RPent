---
title: Hook the handle bar — the geometric catch grasp (primary)
type: technique
scope: task
conditions: Whenever the moka pot must be lifted. Prefer this over any pi0 pick or
  body grasp; the pot body is frictionless and unpinchable.
support: 2
provenance:
- action: add
  proposal: logs/20260815-02:55:18_libero_10_swap_t2_s51/resident_notes.md
  batch: nopi0_t2_arm_a
  date: '2026-08-15'
  evidence:
  - run:20260815-02:55:18_libero_10_swap_t2_s51#seq=15
  - run:20260815-02:55:18_libero_10_swap_t2_s51#seq=17
  - run:20260815-02:55:18_libero_10_swap_t2_s51#seq=19
  counter_evidence: []
---

The pot's handle has a TOP BAR (~1-2 cm thick, on the pot's -y side, top at
rim.z of segment "handle of the moka pot", score ~0.87). The grasp is a
geometric catch — no friction needed, unlike every body/neck pinch:

1. Fingers straight down (rotate_pitch target 0), hover ~7 cm above the
   bar at its measured xy.
2. Descend to z = bar_top (the move lands ~1 cm short, which is correct:
   the 1.3 cm finger tips end just below the bar top, straddling it).
3. set_gripper(+1). SUCCESS SIGNAL: qpos stops at ~0.010 — the bar is
   caught between the fingers. A full close to ~0.004 means air: lift,
   re-measure, retry the descent; never poke the pot itself.
4. Lift and verify with world_extent(mode="held_object"): holding=true
   and the pot's z-range fully above the table.

Checker quirk (measured twice): with the pot base resting on the lit
burner, termination does NOT fire while the bar is still between the
fingers — call release() to free the pot and the checker fires. If the
bar slips out mid-carry over the burner, the falling pot can fire it too.
