---
title: Resolve identity with color/shape probes and wrist close-ups before committing
  a pick
type: technique
scope: common
conditions: When name prompts collide or fail to isolate the target, or when two objects
  match the same description.
support: 4
provenance:
- action: add
  proposal: logs/gate_gen2/proposals/proposal_02.md
  batch: gate_gen2
  date: '2026-08-08'
  evidence:
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=10
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=11
  - run:20260807-14:52:15_libero_object_swap_t3_s0#seq=14
  - run:20260807-19:22:13_libero_object_swap_t3_s0#seq=69
  - run:20260807-19:22:13_libero_object_swap_t3_s0#seq=70
  - run:20260807-19:22:13_libero_object_swap_t3_s0#seq=82
  - run:20260807-18:51:17_libero_object_swap_t1_s0#seq=71
  - run:20260807-19:58:43_libero_object_swap_t6_s0#seq=40
  - run:20260807-19:58:43_libero_object_swap_t6_s0#seq=57
  counter_evidence: []
---

Move the EEF over each candidate and rerun the same prompt set from the wrist camera; add color/shape phrasings from agentview. Commit to a candidate only when at least two independent probes agree on it, or when a close-up probe scores decisively higher than the other candidates. If prompts remain ambiguous, complete a full occupancy enumeration of the table before choosing. Do not commit to a target based on one agentview mask.
