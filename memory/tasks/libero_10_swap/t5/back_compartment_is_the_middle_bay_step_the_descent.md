---
title: Back compartment = the middle bay; step the descent down
type: invariant
scope: task
conditions: When choosing the book's destination bay and planning the descent into
  it.
support: 2
provenance:
- action: add
  proposal: logs/20260815-14:38:27_libero_10_swap_t5_s51/resident_notes.md
  batch: resident_10swap_t5_r2
  date: '2026-08-15'
  evidence:
  - run:20260815-14:38:27_libero_10_swap_t5_s51#seq=39
  - run:20260815-14:38:27_libero_10_swap_t5_s51#seq=8
  counter_evidence: []
---

The caddy's "back compartment" is the MIDDLE of its three bays (between
the full-height divider at y≈-0.07 and the partial wall at y≈-0.215;
same semantics as the sibling cup cell) — the right bay and far-left bay
both seated the book without firing; the middle bay fired twice. VLM and
segment "back/right" verdicts were wrong twice; trust only the divider
geometry from world-map occupancy (SAM's caddy mask is incomplete and
grabs the arm). Grasp the standing book with pi0 ("pick up the black
book", ~0.15 above, verify by held_object book-shaped cloud), carry at
z≈1.24, and STEP the descent (1.24 → 1.18, release at eef z≈1.18): deep
plain move_to below z 1.15 stalls in OSC at this reach. Verify before
release: book center inside the middle bay AND book bottom below the rim.
