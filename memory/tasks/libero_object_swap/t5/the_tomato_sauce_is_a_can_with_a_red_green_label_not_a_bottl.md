---
title: The tomato sauce is a CAN with a red/green label; the standing brown bottle
  is the BBQ distractor
type: invariant
scope: task
conditions: identity phase; whenever an inference of the form "the only bottle must
  be the tomato sauce" is about to be made
support: 3
provenance:
- action: add
  proposal: logs/fix_5f_proposals/p3.md
  batch: fix_5f
  date: '2026-08-12'
  evidence:
  - run:20260811-22:05:02_libero_object_swap_t5_s0#seq=39
  - run:20260812-12:06:23_libero_object_swap_t5_s0#seq=20
  - run:20260812-14:15:31_libero_object_swap_t5_s0#seq=18
  counter_evidence: []
---

The target of this cell is a CAN — silver body, red/green/white "TOMATO
SAUCE" label — not a bottle. The standing dark-brown bottle is the TANGY
BBQ SAUCE distractor. The inference "exactly one bottle exists on the
table, therefore it is the tomato sauce" is invalid by construction here:
the target is not a bottle at all, so the unique bottle is ALWAYS the
distractor. When identity is contested, ask the vision channel to READ THE
LABEL of the candidate (crop it) and cross-check against measured geometry;
an instrument's concrete identification ("dark brown BBQ bottle") outranks
a uniqueness inference, and overriding it requires new measurement, not
reasoning.
