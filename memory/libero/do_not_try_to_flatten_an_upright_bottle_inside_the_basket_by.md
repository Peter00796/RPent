---
title: Do not try to flatten an upright bottle inside the basket by sweeping, pressing,
  or pitching it horizontal in mid-air
type: failure_mode
scope: env
conditions: When a released upright object inside the basket does not trigger termination
  because it protrudes above the rim; when any flattening maneuver is being considered.
support: 1
provenance:
- action: add
  proposal: logs/gate_gen0full_libero_object_swap/proposals/proposal_11.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-12:29:54_libero_object_swap_t9_s0#seq=44
  - run:20260813-12:29:54_libero_object_swap_t9_s0#seq=52
  - run:20260813-12:29:54_libero_object_swap_t9_s0#seq=57
  - run:20260813-12:29:54_libero_object_swap_t9_s0#seq=76
  - run:20260813-12:29:54_libero_object_swap_t9_s0#seq=81
  - run:20260813-12:29:54_libero_object_swap_t9_s0#seq=85
  counter_evidence: []
---

Sweeping or pressing an upright bottle that stands inside the basket will not lay it flat: the sweep only leans it and the press stalls against it. Do not pitch a held bottle horizontal while the EEF is over the basket; the move can stall and the object can be dropped. Regrasp the bottle low with a scripted descend-close-lift, lift it clear of the basket, then lay it flat on the table or re-place it at a lower angle. Verify that the object is still held after every repositioning move.
