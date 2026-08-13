---
title: Disambiguate identical instances by measured geometry against a distinct anchor
type: technique
scope: common
conditions: When two or more instances share a name/color and name-based segmentation
  cannot tell which one is the target; when a successful prompt returns only one of
  several identical-looking objects.
support: 9
provenance:
- action: add
  proposal: logs/gate_gen0full_libero_spatial_swap/proposals/proposal_01.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-13:37:14_libero_spatial_swap_t0_s0#seq=36
  - run:20260813-13:40:37_libero_spatial_swap_t1_s0#seq=38
  - run:20260813-13:43:25_libero_spatial_swap_t2_s0#seq=26
  - run:20260813-13:48:03_libero_spatial_swap_t3_s0#seq=7
  - run:20260813-13:49:21_libero_spatial_swap_t4_s0#seq=61
  - run:20260813-14:03:26_libero_spatial_swap_t5_s0#seq=47
  - run:20260813-14:02:39_libero_spatial_swap_t6_s0#seq=40
  - run:20260813-14:45:02_libero_spatial_swap_t8_s0#seq=49
  - run:20260813-14:19:38_libero_spatial_swap_t9_s0#seq=12
  counter_evidence: []
---

When the task requires choosing one of several identical-looking objects, a text-prompt mask that names the object is only a starting point. Localize each candidate by back-projection or occupancy, then score every candidate against a distinct reference object or surface named by the task relation. Pick the candidate satisfying that spatial relation and corroborate with a wrist or point-segment probe before acting. Do not grow the naming loop when the ambiguity is about which instance, not which word.
---
