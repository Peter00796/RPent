---
title: The basket is MOBILE — release from above the rim only
type: invariant
scope: task
conditions: At every release into the basket, and whenever a placement that looks
  correct does not fire the checker.
support: 3
provenance:
- action: add
  proposal: logs/20260815-08:27:47_libero_10_swap_t1_s51/resident_notes.md
  batch: resident_10swap_t1_r3
  date: '2026-08-15'
  evidence:
  - run:20260815-08:27:47_libero_10_swap_t1_s51#seq=196
  - run:20260815-08:27:47_libero_10_swap_t1_s51#seq=23
  counter_evidence: []
---

Descending the eef deep into the basket (z 0.50-0.52) to release PUSHES
THE BASKET — measured ~16 cm in +x — so boxes land at the basket's OLD
position, outside the checker's frame, and termination never fires even
though everything "looks in". The fix that solved the cell twice: release
each box FROM ABOVE THE RIM (eef z ≈ 0.61, box bottom above the rim ~0.54;
it drops in), first box at the basket's west side, second at the east
side, and re-segment the basket before EVERY placement to confirm it has
not moved. Also: keep pi0_pick max_chunks ≤ 12 for these boxes — larger
budgets let pi0 run its own place and scatter the scene.
