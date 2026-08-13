---
title: Enumerate in low z-bands and identify unnameable targets by elimination
type: technique
scope: common
conditions: When target names and color/shape prompts repeatedly return found=false;
  when a target may be flat and low-profile; when an occupancy sweep at normal table
  height finds no unclaimed cluster.
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
- action: revise
  proposal: logs/gate_gen0full_libero_10_swap/proposals/proposal_02.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-17:02:11_libero_10_swap_t1_s0#seq=41
  - run:20260813-17:02:11_libero_10_swap_t1_s0#seq=100
  - run:20260813-17:02:11_libero_10_swap_t1_s0#seq=117
  - run:20260813-17:02:11_libero_10_swap_t1_s0#seq=118
  counter_evidence: []
---

Flat targets sit below the band that tall objects occupy. Finish the normal-band enumeration quickly, then lower the occupancy floor to just above the table surface and repeat once. An unclaimed low-band cluster is the target by elimination. Do not spend more name variants after the low-band sweep is complete; act on the best-supported cluster.
