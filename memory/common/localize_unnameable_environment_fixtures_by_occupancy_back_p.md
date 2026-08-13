---
title: Localize unnameable environment fixtures by occupancy/back-projection, not
  by repeated segmentation
type: technique
scope: common
conditions: When segmentation prompts for non-object fixtures (stove, drawer cavity,
  microwave, caddy compartments) fail, return false, or return garbage masks; when
  VLM spatial answers about fixtures are inconsistent; when a fixture has a flat or
  box-like shape with no reliable text grounding.
support: 4
provenance:
- action: add
  proposal: logs/gate_gen0full_libero_10_swap/proposals/proposal_08.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-17:32:49_libero_10_swap_t8_s0#seq=4
  - run:20260813-17:32:49_libero_10_swap_t8_s0#seq=8
  - run:20260813-17:32:49_libero_10_swap_t8_s0#seq=26
  - run:20260813-17:33:31_libero_10_swap_t3_s0#seq=5
  - run:20260813-17:33:31_libero_10_swap_t3_s0#seq=19
  - run:20260813-19:02:53_libero_10_swap_t9_s0#seq=4
  - run:20260813-19:02:53_libero_10_swap_t9_s0#seq=28
  - run:20260813-19:02:53_libero_10_swap_t9_s0#seq=36
  - run:20260813-18:08:26_libero_10_swap_t5_s0#seq=5
  - run:20260813-18:08:26_libero_10_swap_t5_s0#seq=79
  counter_evidence: []
---

Fixtures often do not support text grounding. After one failed segmentation prompt and one garbage mask for a fixture, stop segmenting it by name. Map the region geometrically: occupancy bands for raised platforms, back-projection of image regions, wrist-camera occupancy scans, and point prompts for cavity openings. Trust the geometric model over VLM spatial claims about fixtures.
