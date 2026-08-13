---
title: Validate wrist-camera spatial language by back-projecting image axes before
  choosing a compartment or grasp axis
type: technique
scope: common
conditions: When wrist VLM returns spatial labels ("front", "back", "left", "right")
  for a receptacle or object; when aligning gripper fingers to an object axis at a
  rotated yaw.
support: 2
provenance:
- action: add
  proposal: logs/gate_gen0full_libero_10_task/proposals/proposal_09.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-15:44:17_libero_10_task_t5_s0#seq=35
  - run:20260813-15:44:17_libero_10_task_t5_s0#seq=39
  - run:20260813-15:44:17_libero_10_task_t5_s0#seq=40
  - run:20260813-15:27:56_libero_10_task_t8_s0#seq=28
  - run:20260813-15:27:56_libero_10_task_t8_s0#seq=29
  - run:20260813-15:27:56_libero_10_task_t8_s0#seq=43
  - run:20260813-15:27:56_libero_10_task_t8_s0#seq=44
  counter_evidence: []
---

The wrist image is a moving frame; VLM "front/back" or "left/right" labels from it are not reliable. Before choosing a compartment or a grasp axis, back-project a few rows/columns through the wrist calibration to learn what the image axes mean in world coordinates. At rotated yaw, pixel back-projection can collapse to the table plane; then fall back to wrist-camera extrinsics to compute the closing axis.
