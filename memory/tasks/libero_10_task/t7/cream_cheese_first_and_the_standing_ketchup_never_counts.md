---
title: Cream cheese first; a standing ketchup never counts as "in"
type: failure_mode
scope: task
conditions: When ordering the two placements, and when the ketchup is about to be
  released into the basket.
support: 3
provenance:
- action: add
  proposal: logs/20260815-11:44:34_libero_10_task_t7_s51/run.log
  batch: resident_10task_t7_r1
  date: '2026-08-15'
  evidence:
  - run:20260815-11:44:34_libero_10_task_t7_s51#seq=14
  - run:20260815-11:44:34_libero_10_task_t7_s51#seq=31
  counter_evidence: []
---

Three measured walls, unsolved as of r1 (budget death at 300 turns):
(1) order matters — the cream cheese placed FIRST into the empty basket
works (verified twice); placed after the ketchup it perches on the
bottle's top (z≈0.59, above the rim 0.534) and never counts. (2) The
ketchup released standing ends with its base ON the near rim or poking
above the rim — "in" never fires for a standing bottle in this shallow
basket. (3) Sweeping the standing bottle flat with pi0_doubled knocks
the seated cream cheese OUT over the far rim. Open problem for r2: get
the ketchup in LYING or fully below the rim — candidates: release from
directly over the basket center high enough to topple inward, or lay the
bottle on the table first and roll/slide it in; never sweep inside the
basket after the cheese is placed.
