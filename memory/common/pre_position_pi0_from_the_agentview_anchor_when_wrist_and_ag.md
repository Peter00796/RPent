---
title: Pre-position pi0 from the agentview anchor when wrist and agentview disagree
type: technique
scope: common
conditions: Before every pi0_pick, especially after a previous pick failed or hit
  the wrong object; when wrist and agentview anchors disagree.
support: 1
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_04.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-14:18:46_libero_object_swap_t0_s0#seq=24
  - run:20260807-14:18:46_libero_object_swap_t0_s0#seq=27
  - run:20260807-14:18:46_libero_object_swap_t0_s0#seq=31
  - run:20260807-14:18:46_libero_object_swap_t0_s0#seq=33
  counter_evidence: []
- action: revise
  proposal: logs/gate_gen0full_libero_object_swap/proposals/proposal_03.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-11:49:34_libero_object_swap_t0_s0#seq=21
  - run:20260813-12:07:21_libero_object_swap_t2_s0#seq=10
  - run:20260813-12:10:54_libero_object_swap_t4_s0#seq=15
  - run:20260813-12:16:54_libero_object_swap_t6_s0#seq=26
  - run:20260813-12:16:54_libero_object_swap_t6_s0#seq=33
  - run:20260813-12:16:54_libero_object_swap_t6_s0#seq=76
  - run:20260813-12:26:26_libero_object_swap_t7_s0#seq=8
  counter_evidence: []
---

Do not issue pi0_pick from home or from a hover far from the target. First move the EEF directly above the geometrically confirmed object position, then issue the pick prompt. If a wrist read and the agentview anchor disagree, trust the agentview-derived anchor. Pi0 picks that connect are the ones launched from directly above the intended object. Verify every pick geometrically after issuing it.
