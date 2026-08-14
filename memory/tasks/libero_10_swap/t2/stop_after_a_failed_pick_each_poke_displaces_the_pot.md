---
title: Stop after a failed pick — each poke displaces the pot
type: failure_mode
scope: task
conditions: Immediately after a pi0_pick that did not yield a geometrically verified
  hold.
support: 4
provenance:
- action: add
  proposal: logs/20260814-16:02:54_libero_10_swap_t2_s51/resident_notes.md
  batch: resident_10swap_t2_r2
  date: '2026-08-14'
  evidence:
  - run:20260814-16:02:54_libero_10_swap_t2_s51#seq=5
  - run:20260814-16:02:54_libero_10_swap_t2_s51#seq=8
  counter_evidence: []
---

A failed pick is not free: air-grasps and half-lifts shove the pot — up to
~24 cm off-origin, into the frypan, or onto its side — and a lying pot is
effectively unrecoverable (pi0 will not re-engage it and further pokes
scatter it). After one failed pick, re-localize the pot before ANY retry;
if it has left its upright pose or the retry also fails verification, stop
attempting picks rather than spending the episode scattering the pot.
