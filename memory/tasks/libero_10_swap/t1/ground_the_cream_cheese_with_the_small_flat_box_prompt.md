---
title: Ground the cream cheese with the small-flat-box prompt
type: technique
scope: task
conditions: At the start of the basket cell, when localizing the cream cheese box —
  and whenever a "white cylinder" candidate appears near x=-0.46.
support: 2
provenance:
- action: add
  proposal: logs/20260814-15:44:20_libero_10_swap_t1_s51/run.log
  batch: resident_10swap_t1_r1r2
  date: '2026-08-15'
  evidence:
  - run:20260814-14:58:32_libero_10_swap_t1_s51#seq=39
  - run:20260814-15:44:20_libero_10_swap_t1_s51#seq=13
  counter_evidence: []
---

The white cylinder near x = -0.46 is a FIXED table structure, not the
cream cheese — it never moves and returns identical readings every step;
one run burned ~15 steps and 43 VLM queries on it. Ground the target as
"the small flat cream cheese box" and pick with pi0 from a ~10 cm
pre-position (verified working twice). Identity check before any motion:
a candidate that has never moved across steps and matches a structure
position is scenery.
