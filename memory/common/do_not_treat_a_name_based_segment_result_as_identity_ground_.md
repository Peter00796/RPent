---
title: Do not treat a name-based segment result as identity ground truth
type: invariant
scope: common
conditions: When a target object is identified by language prompts, and when look-alike
  objects share category/color names.
support: 4
provenance:
- action: add
  proposal: logs/gate_gen2/proposals/proposal_01.md
  batch: gate_gen2
  date: '2026-08-08'
  evidence:
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=2
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=6
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=7
  - run:20260807-15:52:13_libero_object_swap_t8_s0#seq=3
  - run:20260807-15:52:13_libero_object_swap_t8_s0#seq=17
  - run:20260807-20:15:39_libero_object_swap_t7_s0#seq=15
  - run:20260807-20:15:39_libero_object_swap_t7_s0#seq=17
  - run:20260807-19:38:26_libero_object_swap_t5_s0#seq=16
  - run:20260807-19:38:26_libero_object_swap_t5_s0#seq=17
  - run:20260807-19:38:26_libero_object_swap_t5_s0#seq=22
  counter_evidence: []
---

A `found=true` from one text prompt is not proof that the prompt's category is the object's identity, and a `found=false` for the canonical task name is not proof the object is absent. Several task names can collapse onto one mask, while a color/shape phrasing may be the only one that separates the true target. Before committing a pick, require either independent phrasings landing on the same candidate, a close-up wrist probe that discriminates candidates, or an occupancy/back-projection map that locates the candidate geometrically. When no name succeeds, do not keep re-probing; switch to geometric scene enumeration and act on the best candidate.
