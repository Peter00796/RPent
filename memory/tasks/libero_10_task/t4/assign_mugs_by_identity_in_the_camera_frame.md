---
title: Assign mugs by identity, left/right in the camera frame
type: invariant
scope: task
conditions: Before planning any placement in the dual-mug cell — deciding which mug
  goes to which plate.
support: 2
provenance:
- action: add
  proposal: logs/20260814-15:00:33_libero_10_task_t4_s51/run.log
  batch: resident_10task_t4_r1r2
  date: '2026-08-15'
  evidence:
  - run:20260814-15:00:33_libero_10_task_t4_s51#seq=25
  - run:20260814-15:47:45_libero_10_task_t4_s51#seq=28
  counter_evidence: []
---

"Left plate" and "right plate" in the task language are the CAMERA
(agentview) frame, not the robot frame — the two are opposite here. The
assignment is by mug identity: the yellow-and-white mug goes to the
image-LEFT (world −y) plate; the "white mug" (the porcelain one) goes to
the image-RIGHT (world +y) plate. The robot-frame reading fails
deterministically: six attempts placed both mugs correctly by robot-left
convention — including dead-center within 3 mm — and the checker never
fired. Do not spend attempts on placement accuracy before fixing the
frame convention.
