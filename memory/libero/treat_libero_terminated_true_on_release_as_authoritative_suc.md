---
title: Treat libero_terminated=true on release as authoritative success; occluded
  post-release checks are audit-only
type: invariant
scope: env
conditions: In libero tasks where the environment flag fires on the release call;
  when post-release point-cloud checks are occluded by the arm or the exclusion radius;
  when wrist and agentview placement inspections disagree.
support: 8
provenance:
- action: add
  proposal: logs/gate_gen0full_libero_spatial_swap/proposals/proposal_04.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-13:37:14_libero_spatial_swap_t0_s0#seq=36
  - run:20260813-13:43:25_libero_spatial_swap_t2_s0#seq=26
  - run:20260813-13:48:03_libero_spatial_swap_t3_s0#seq=72
  - run:20260813-13:49:21_libero_spatial_swap_t4_s0#seq=61
  - run:20260813-14:03:26_libero_spatial_swap_t5_s0#seq=47
  - run:20260813-14:12:42_libero_spatial_swap_t7_s0#seq=45
  - run:20260813-14:45:02_libero_spatial_swap_t8_s0#seq=49
  - run:20260813-14:19:38_libero_spatial_swap_t9_s0#seq=33
  counter_evidence: []
---

The environment's end-of-episode flag is the only authoritative completion signal. Once release returns with libero_terminated=true, do not start a re-pick because a post-release occupancy compare looks occluded, or because one VLM placement statement disagrees. Keep post-release checks as audit for the recipe; they must not veto an already-terminated episode. If the flag does not fire on release, do not treat the release as success; use the placement-verification failure mode instead.
---
