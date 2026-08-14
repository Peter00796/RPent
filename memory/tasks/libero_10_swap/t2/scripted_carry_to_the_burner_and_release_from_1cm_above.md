---
title: Scripted carry to the burner, release from ~1 cm above
type: technique
scope: task
conditions: When a pi0 grasp of the pot has been geometrically verified but pi0 did
  not finish the place itself.
support: 2
provenance:
- action: add
  proposal: logs/20260814-16:02:54_libero_10_swap_t2_s51/resident_notes.md
  batch: resident_10swap_t2_r2
  date: '2026-08-14'
  evidence:
  - run:20260814-16:02:54_libero_10_swap_t2_s51#seq=12
  - run:20260814-16:02:54_libero_10_swap_t2_s51#seq=15
  - run:20260814-16:02:54_libero_10_swap_t2_s51#seq=16
  counter_evidence: []
---

Carry scripted with gripper +1 the whole way: waypoint over open table
(clear of the frypan), then re-query held_object for the fresh pot-to-eef
offset, then hover at burner_xy minus that offset at a safe height, then
descend to eef z ≈ stove_top + pot-base offset (pot base ~1 cm above the
burner) and release(). Watch the jaw during transit: a closing jaw means
the pot is sliding out — stop and re-verify instead of continuing the
carry. Termination fires on contact with the burner of an already-on
stove; it can also fire mid-carry or mid-descent with the gripper still
closed — do not require a release before believing it.
