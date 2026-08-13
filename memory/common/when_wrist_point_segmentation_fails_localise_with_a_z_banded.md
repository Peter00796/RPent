---
title: When wrist point-segmentation fails, localise with a z-banded wrist back-projection
type: technique
scope: common
conditions: When a wrist-camera point-segmentation is rejected as the table plane
  or returns found=false before a pick; when an agentview anchor needs wrist confirmation.
support: 1
provenance:
- action: add
  proposal: logs/gate_gen0full_libero_object_swap/proposals/proposal_09.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-12:16:10_libero_object_swap_t5_s0#seq=25
  - run:20260813-12:16:10_libero_object_swap_t5_s0#seq=26
  - run:20260813-12:16:10_libero_object_swap_t5_s0#seq=27
  counter_evidence: []
---

If the wrist-camera point-segment at the image centre returns only a table-plane mask, do not treat the wrist view as unusable. Re-project the same wrist region with a low z-band above the table and take the upper-surface median as the object anchor. Use that z-banded back-projection, not the raw point-segment, for the pre-pick localisation.
