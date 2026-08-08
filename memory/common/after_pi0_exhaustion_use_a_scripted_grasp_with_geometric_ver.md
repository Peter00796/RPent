---
title: After pi0 exhaustion, use a scripted grasp with geometric verification
type: technique
scope: common
conditions: When pi0 has failed repeatedly and the object is still on the table; when
  the first scripted descent stalls.
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
- action: revise
  proposal: logs/gate_gen2/proposals/proposal_09.md
  batch: gate_gen2
  date: '2026-08-08'
  evidence:
  - run:20260807-18:33:42_libero_object_swap_t0_s0#seq=87
  - run:20260807-18:33:42_libero_object_swap_t0_s0#seq=88
  - run:20260807-19:58:43_libero_object_swap_t6_s0#seq=94
  - run:20260807-19:58:43_libero_object_swap_t6_s0#seq=98
  - run:20260807-19:07:14_libero_object_swap_t2_s0#seq=71
  - run:20260807-15:01:22_libero_object_swap_t4_s0#seq=47
  - run:20260807-15:01:22_libero_object_swap_t4_s0#seq=54
  counter_evidence: []
---

Keep the fallback: move to the agentview footprint center, descend to just above the object, close, lift, and verify with held-object. Add the caveat that a move-to/move-pose descent can stall at a low height in some table regions; do not repeat the same stalled descent. Instead retreat to a clear/home pose and either re-try pi0 from home or re-localize and approach from a different direction. A scripted grasp is not a guaranteed recovery; only transport after geometric verification.
