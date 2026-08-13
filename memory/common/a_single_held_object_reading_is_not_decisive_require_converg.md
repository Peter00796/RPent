---
title: A single held-object reading is not decisive; require convergent evidence
type: failure_mode
scope: common
conditions: After a pick, during transport, when held_object contradicts other evidence;
  when the reported gripper width is above the held-object tool's open threshold;
  when the held object is small relative to point-cloud resolution.
support: 5
provenance:
- action: add
  proposal: logs/gate_gen2/proposals/proposal_04.md
  batch: gate_gen2
  date: '2026-08-08'
  evidence:
  - run:20260807-15:01:22_libero_object_swap_t4_s0#seq=38
  - run:20260807-15:01:22_libero_object_swap_t4_s0#seq=45
  - run:20260807-18:51:17_libero_object_swap_t1_s0#seq=103
  - run:20260807-18:51:17_libero_object_swap_t1_s0#seq=109
  - run:20260807-15:52:13_libero_object_swap_t8_s0#seq=45
  - run:20260807-15:52:13_libero_object_swap_t8_s0#seq=48
  - run:20260807-20:22:07_libero_object_swap_t8_s0#seq=58
  - run:20260807-20:22:07_libero_object_swap_t8_s0#seq=61
  counter_evidence: []
- action: endorse
  proposal: logs/gate_gen3/proposals/proposal_09.md
  batch: gate_gen3
  date: '2026-08-10'
  evidence:
  - run:20260808-12:34:51_libero_object_swap_t8_s0#seq=55
  - run:20260808-12:34:51_libero_object_swap_t8_s0#seq=60
  - run:20260808-12:34:51_libero_object_swap_t8_s0#seq=72
  - run:20260808-12:34:51_libero_object_swap_t8_s0#seq=75
  - run:20260808-12:34:51_libero_object_swap_t8_s0#seq=87
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen0full_libero_10_task/proposals/proposal_03.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-15:27:56_libero_10_task_t8_s0#seq=77
  - run:20260813-15:27:56_libero_10_task_t8_s0#seq=79
  - run:20260813-15:27:56_libero_10_task_t8_s0#seq=81
  - run:20260813-14:54:42_libero_10_task_t6_s0#seq=71
  - run:20260813-14:54:42_libero_10_task_t6_s0#seq=74
  - run:20260813-14:54:42_libero_10_task_t6_s0#seq=72
  - run:20260813-14:02:23_libero_10_task_t0_s0#seq=51
  - run:20260813-14:02:23_libero_10_task_t0_s0#seq=63
  - run:20260813-14:02:23_libero_10_task_t0_s0#seq=65
  counter_evidence: []
---

held_object has hardware-like biases: a clamp wider than roughly 0.06 m can be read as "open", a small held item can produce no cluster, and a check taken with the EEF inside the queried volume can return table/container points. Do not let a single false or true decide a grasp. After every pick, compare origin-box voxel removal at a clearance pose and add a wrist-camera close-up. For small objects, origin-box emptiness is the primary signal because held_object may never see them.
