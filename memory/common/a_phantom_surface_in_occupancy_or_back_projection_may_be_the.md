---
title: A phantom surface in occupancy or back-projection may be the arm; re-probe
  after moving the arm
type: failure_mode
scope: common
conditions: When an elevated occupancy band or a back-projected plate appears while
  the arm is in/near the probe volume; when a "static" surface is about to be turned
  into a goal landmark.
support: 3
provenance:
- action: add
  proposal: logs/gate_gen0full_libero_goal_swap/proposals/proposal_05.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-12:17:11_libero_goal_swap_t0_s0#seq=10
  - run:20260813-12:17:11_libero_goal_swap_t0_s0#seq=25
  - run:20260813-12:17:11_libero_goal_swap_t0_s0#seq=75
  - run:20260813-12:17:11_libero_goal_swap_t0_s0#seq=78
  - run:20260813-13:10:29_libero_goal_swap_t4_s0#seq=25
  - run:20260813-13:10:29_libero_goal_swap_t4_s0#seq=32
  - run:20260813-13:10:29_libero_goal_swap_t4_s0#seq=34
  - run:20260813-13:10:29_libero_goal_swap_t4_s0#seq=47
  - run:20260813-14:03:19_libero_goal_swap_t9_s0#seq=11
  - run:20260813-14:03:19_libero_goal_swap_t9_s0#seq=17
  - run:20260813-14:03:19_libero_goal_swap_t9_s0#seq=72
  counter_evidence: []
---

A back-projected "surface" that appears in an occupancy band while the arm is in or near that volume may be the arm. Before committing to a fixture, re-probe after moving the arm; static furniture gives identical world points before/after an arm lift, while arm-contaminated pixels move or vanish. Phantom high-z surfaces waste whole episodes; the wrist camera is the tie-breaker.
