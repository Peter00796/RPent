---
title: Turn on the stove first, from a knob pre-position
type: technique
scope: task
conditions: At the start of the episode, before any moka-pot manipulation.
support: 3
provenance:
- action: add
  proposal: logs/20260814-16:02:54_libero_10_swap_t2_s51/resident_notes.md
  batch: resident_10swap_t2_r2
  date: '2026-08-14'
  evidence:
  - run:20260814-16:02:54_libero_10_swap_t2_s51#seq=19
  - run:20260814-16:02:54_libero_10_swap_t2_s51#seq=27
  counter_evidence: []
---

Do the stove before the pot: segment "stove knob round dial", move_to a
pre-position ~0.06 m above the knob top, then pi0_doubled("turn on the
stove", 20). The contact skill descends and turns the knob. Ignore the
skill's own success flag (it mirrors only task termination); if needed,
confirm the burner glows with one inspect_image on the full agentview
frame. All three solved attempts (1, 4, 6) used exactly this opening.
