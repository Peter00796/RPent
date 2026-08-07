---
title: After pi0 exhaustion, use a scripted grasp with geometric verification
type: technique
scope: common
conditions: Applies when pi0_pick has failed multiple times or its reported successes
  cannot be verified geometrically.
support: 2
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_06.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-15:01:22_libero_object_swap_t4_s0#seq=47
  - run:20260807-15:01:22_libero_object_swap_t4_s0#seq=54
  - run:20260807-15:21:05_libero_object_swap_t6_s0#seq=96
  - run:20260807-15:21:05_libero_object_swap_t6_s0#seq=100
  counter_evidence:
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=38
---

A scripted move-above, descend, close, lift sequence is a viable bounded fallback once the policy pick ladder is exhausted. Verify with held_object and occupancy before carrying; if the scripted grasp touches nothing or stalls, retreat rather than pushing farther into the scene.
---
