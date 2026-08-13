---
title: Use SAM point-prompt segmentation with VLM crop naming when text grounding
  fails
type: technique
scope: common
conditions: When all text-prompt segmentations for the target return found=false;
  when a VLM scene enumeration has produced a candidate pixel/region but no mask.
support: 1
provenance:
- action: add
  proposal: logs/gate_gen0full_libero_object_swap/proposals/proposal_08.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-12:42:22_libero_object_swap_t8_s0#seq=2
  - run:20260813-12:42:22_libero_object_swap_t8_s0#seq=4
  - run:20260813-12:42:22_libero_object_swap_t8_s0#seq=8
  - run:20260813-12:42:22_libero_object_swap_t8_s0#seq=11
  - run:20260813-12:42:22_libero_object_swap_t8_s0#seq=35
  - run:20260813-12:42:22_libero_object_swap_t8_s0#seq=36
  counter_evidence: []
---

When the target name cannot be grounded by any phrasing, stop rephrasing. Use the VLM's full-scene enumeration to choose a candidate pixel/region, run SAM in point-prompt mode on that pixel, and then name the resulting mask with a per-crop VLM read. Only back-project the mask after the crop read agrees. This path can replace text grounding for identity and position.
