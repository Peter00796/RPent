---
title: Enumerate in low z-bands and identify unnameable targets by elimination
type: technique
scope: common
conditions: When target-name prompts and color/shape prompts repeatedly return found=false,
  or when a target may be a flat low-profile object that earlier occupancy sweeps
  would miss.
support: 2
provenance:
- action: add
  proposal: logs/gate_gen3/proposals/proposal_01.md
  batch: gate_gen3
  date: '2026-08-10'
  evidence:
  - run:20260808-11:14:17_libero_object_swap_t1_s0#seq=63
  - run:20260808-11:14:17_libero_object_swap_t1_s0#seq=74
  - run:20260808-11:14:17_libero_object_swap_t1_s0#seq=85
  - run:20260808-12:34:51_libero_object_swap_t8_s0#seq=26
  - run:20260808-12:34:51_libero_object_swap_t8_s0#seq=49
  - run:20260808-12:34:51_libero_object_swap_t8_s0#seq=87
  counter_evidence: []
---

Do not grow the naming loop when the target cannot be segmented. Segment every other object that does respond, then tile the tabletop with occupancy/back-projection boxes and repeat the sweep with the z floor lowered to just above the table surface; flat targets sit below the initial scan floor and appear only after the band is lowered. An unclaimed cluster after that enumeration is the target by elimination. If no new cluster appears and the enumeration is complete, stop re-scanning and act on the best-supported candidate.
