---
curated: gen1b_owner_order 2026-08-14
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

WHEN: before pi0_pick or any contact policy.
RULE: first move the open gripper directly above the confirmed target
(about 0.15 above), then call the policy. Launched from home or a far
hover, the policy acts on the wrong thing. When wrist and agentview
disagree, the agentview anchor wins.
WHY: grasp-width signatures 0.002 (from home) vs 0.039 (pre-positioned),
reproduced on two cells.
