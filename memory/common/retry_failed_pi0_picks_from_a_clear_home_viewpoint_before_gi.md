---
title: Retry failed Pi0 picks from a clear/home viewpoint before giving up
type: technique
scope: common
conditions: When an air-grasp has been diagnosed (pi0 status success but nothing held,
  or origin box empty and no held object); when the run has just read retry or flat-target
  guidance and then returns to occupancy probing.
support: 1
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_05.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=28
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=33
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=43
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=44
  counter_evidence:
  - run:20260807-16:08:47_libero_object_swap_t9_s0#seq=59
- action: revise
  proposal: logs/gate_gen3/proposals/proposal_04.md
  batch: gate_gen3
  date: '2026-08-10'
  evidence:
  - run:20260808-11:00:42_libero_object_swap_t0_s0#seq=68
  - run:20260808-11:00:42_libero_object_swap_t0_s0#seq=71
  - run:20260808-11:00:42_libero_object_swap_t0_s0#seq=77
  - run:20260808-11:00:42_libero_object_swap_t0_s0#seq=78
  - run:20260808-12:47:32_libero_object_swap_t9_s0#seq=34
  - run:20260808-12:47:32_libero_object_swap_t9_s0#seq=47
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen4/proposals/proposal_04.md
  batch: gate_gen4
  date: '2026-08-10'
  evidence:
  - run:20260810-17:57:07_libero_object_swap_t3_s0#seq=85
  - run:20260810-17:57:07_libero_object_swap_t3_s0#seq=87
  - run:20260810-17:57:07_libero_object_swap_t3_s0#seq=92
  - run:20260810-17:57:07_libero_object_swap_t3_s0#step=12
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen5/proposals/proposal_03.md
  batch: gate_gen5
  date: '2026-08-11'
  evidence:
  - run:20260810-20:52:58_libero_object_swap_t6_s0#seq=87
  - run:20260810-20:52:58_libero_object_swap_t6_s0#seq=93
  - run:20260810-20:52:58_libero_object_swap_t6_s0#seq=94
  - run:20260810-20:52:58_libero_object_swap_t6_s0#seq=102
  - run:20260810-20:52:58_libero_object_swap_t6_s0#seq=112
  counter_evidence: []
---

Once a pick is geometrically confirmed as an air-grasp, re-picking is the next action, not optional. Locate the object's new footprint from a low z-band or the wrist camera and issue a pick from the fresh coordinates. Re-enumerating the table after a failed pick consumes the episode; do not return to perception once the failure class is diagnosed.
---
