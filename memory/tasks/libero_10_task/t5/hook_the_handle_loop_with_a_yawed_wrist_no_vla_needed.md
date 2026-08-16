---
title: Clamp the handle loop with a yawed wrist — no VLA needed
type: technique
scope: task
conditions: When the mug must be lifted and no VLA pick is available — the 0.10 m
  body exceeds the jaw; plan_grasp finds the handle loop as the only candidate.
support: 2
provenance:
- action: add
  proposal: logs/20260815-23:44:08_libero_10_task_t5_s51/resident_notes.md
  batch: plangrasp_t5_r1
  date: '2026-08-16'
  evidence:
  - run:20260815-23:44:08_libero_10_task_t5_s51#seq=25
  - run:20260815-23:44:08_libero_10_task_t5_s51#seq=48
  counter_evidence: []
---

plan_grasp on a box around the mug's handle side returns the loop as a
~0.014 m candidate with close-axis along world x. Execute it scripted:
(1) rotate_wrist to yaw pi/2 so the fingers close along x — the rotation
drifts the eef ~0.17 m in +y, re-position after; (2) hover over the
measured loop center, descend so the fingertips sit MID-band of the loop
(band_top − ~0.02): fingertips at the band top close through air (qpos
collapses to ~0.001), mid-band clamps; (3) set_gripper +1 — clamp
signature qpos ~0.020, NOT ~0.001; (4) lift and verify with held_object
(cloud hangs ~0.05 below the eef) plus origin-box collapse, and
re-measure the held offset EVERY grasp. Place into the caddy: aim the
mug center ~0.02 deeper (−x) than the nominal back-compartment center
(the mug drifts ~+0.027 toward the camera as it falls), descend to
rim + 0.06, ACCEPT the stall there — grinding lower pushes the mug out
over the front wall — then release().
