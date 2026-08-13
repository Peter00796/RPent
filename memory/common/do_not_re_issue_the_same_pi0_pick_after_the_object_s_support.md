---
title: Do not re-issue the same pi0 pick after the object's support changes; re-localize
  and change the approach first
type: failure_mode
scope: common
conditions: When a pick prompt succeeded for an object on one support and the same
  object now sits on a different support; when repeated re-picks from the new support
  all fail; when the failure includes descents that drift to other objects.
support: 1
provenance:
- action: add
  proposal: logs/gate_gen0full_libero_10_swap/proposals/proposal_11.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-16:37:01_libero_10_swap_t4_s0#seq=12
  - run:20260813-16:37:01_libero_10_swap_t4_s0#seq=38
  - run:20260813-16:37:01_libero_10_swap_t4_s0#seq=74
  - run:20260813-16:37:01_libero_10_swap_t4_s0#seq=80
  - run:20260813-16:37:01_libero_10_swap_t4_s0#seq=85
  counter_evidence: []
---

Pi0 pick success is support-dependent. A prompt that reliably grasps an object from a clear table can fail every time the same object sits flush on a plate, in a drawer, or against other geometry. When the support changes, do not issue the same prompt from the same pose. Re-localize the object's current footprint, move the gripper to a new pre-position, and either change the prompt/approach or reposition the object onto a table-like surface before re-picking.
