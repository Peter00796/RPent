---
title: Discard held-object point clouds contaminated by the container near the basket
type: failure_mode
scope: env
conditions: Applies when the wrist is over or near the basket and held_object returns
  a shape_warning, an implausibly wide span, or a failed wrist segmentation.
support: 4
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_08.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-14:18:46_libero_object_swap_t0_s0#seq=42
  - run:20260807-14:18:46_libero_object_swap_t0_s0#seq=45
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=47
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=48
  - run:20260807-15:52:13_libero_object_swap_t8_s0#seq=69
  - run:20260807-16:08:47_libero_object_swap_t9_s0#seq=40
  counter_evidence: []
---

When the EEF is over the basket, the held-object mask can include the container, producing an implausibly wide span. Do not use such a reading to compute release coordinates. Record a clean held-object offset in open air before the final approach; when the contaminated warning appears, use that clean offset or agentview re-segmentation so that the object, not the EEF, is centered over the opening.
---
