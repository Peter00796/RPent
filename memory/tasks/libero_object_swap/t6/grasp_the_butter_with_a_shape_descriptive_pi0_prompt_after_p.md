---
title: Grasp the butter with a shape-descriptive pi0 prompt after playbook localisation
type: technique
scope: task
conditions: after the butter is localised by the low-slab recipe; immediately before
  the pi0_pick call
support: 1
provenance:
- action: add
  proposal: logs/playbook_t6b/proposals/grasp_prompt.md
  batch: playbook_t6b
  date: '2026-08-11'
  evidence:
  - run:20260811-06:20:22_libero_object_swap_t6_s52#seq=32
  - run:20260811-06:20:22_libero_object_swap_t6_s52#seq=35
  - run:20260811-06:20:22_libero_object_swap_t6_s52#step=2
  counter_evidence: []
- action: revise
  proposal: logs/resident_libero_object_swap_t6/mine_01/proposals/proposal_01.md
  batch: resident_mine_01
  date: '2026-08-11'
  evidence:
  - run:20260811-12:50:41_libero_object_swap_t6_s51#seq=4
  - run:20260811-12:50:41_libero_object_swap_t6_s51#seq=5
  - run:20260811-12:50:41_libero_object_swap_t6_s51#seq=7
  - run:20260811-12:50:41_libero_object_swap_t6_s51#seq=14
  counter_evidence: []
---

Do not call pi0_pick from HOME. The same shape-descriptive pick issued from HOME reports success but closes the fingers to ~0.002 (air grasp); after first moving the eef to a pre-position above the localised butter footprint, the same pick closes to ~0.039 and pinches the 0.040 m slab. Recipe: localise, pre-position above the localised anchor, then issue the shape-descriptive pick.
