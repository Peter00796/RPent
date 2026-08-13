---
title: When pi0 contact skill cannot open a drawer, use clamped slow pulls with geometric
  handle re-verification
type: technique
scope: common
conditions: When pi0_doubled or a contact-skill prompt returns non-opening behaviour
  on a drawer; when repeated prompt/chunk variants fail to move the handle.
support: 1
provenance:
- action: add
  proposal: logs/gate_gen0full_libero_goal_swap/proposals/proposal_09.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-13:00:08_libero_goal_swap_t3_s0#seq=20
  - run:20260813-13:00:08_libero_goal_swap_t3_s0#seq=26
  - run:20260813-13:00:08_libero_goal_swap_t3_s0#seq=38
  - run:20260813-13:00:08_libero_goal_swap_t3_s0#seq=63
  - run:20260813-13:00:08_libero_goal_swap_t3_s0#seq=64
  - run:20260813-13:00:08_libero_goal_swap_t3_s0#seq=83
  - run:20260813-13:00:08_libero_goal_swap_t3_s0#seq=86
  - run:20260813-13:00:08_libero_goal_swap_t3_s0#seq=89
  - run:20260813-13:00:08_libero_goal_swap_t3_s0#seq=90
  counter_evidence: []
---

pi0_doubled/contact skills are not a reliable drawer-opening primitive: repeated varied prompts and chunk budgets may never open the drawer. After two failed attempts, switch to a scripted handle grasp and clamped slow pull: rotate the wrist to yaw≈π/2 to extend low reach, close over the handle and verify contact by the eef being drawn in, then pull with very small step_clip and action_scale. Re-segment the handle after every pull; only the slow pull moves it (~1 cm), and ratchet cycles can slip. Do not expect a single pull to open the drawer.
