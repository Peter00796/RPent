---
title: Pre-position the EEF aligned with the contact target before invoking a contact
  policy; verify target-state change by geometry
type: technique
scope: common
conditions: before calling a policy that performs contact (pi0_doubled, handle, knob);
  after a contact attempt from a distant hover or stalled pose fails to change the
  target.
support: 3
provenance:
- action: add
  proposal: logs/gate_gen0full_libero_goal_task/proposals/proposal_06.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-09:29:18_libero_goal_task_t0_s0#seq=57
  - run:20260813-09:29:18_libero_goal_task_t0_s0#seq=79
  - run:20260813-10:43:22_libero_goal_task_t3_s0#seq=33
  - run:20260813-10:43:22_libero_goal_task_t3_s0#seq=56
  - run:20260813-10:43:22_libero_goal_task_t3_s0#seq=62
  - run:20260813-11:36:25_libero_goal_task_t7_s0#seq=24
  - run:20260813-11:36:25_libero_goal_task_t7_s0#seq=32
  counter_evidence: []
---

A contact policy launched from a distant hover or a stalled pose tends to drift toward open space instead of the target. Before invoking it, move the EEF to a clear pose aligned with the localized contact point. After the call, verify the target changed (handle slot emptied, handle translated, knob state) with occupancy or handle geometry; do not trust a VLM open/closed verdict. If the first call changed nothing, re-pre-position and call again from the aligned pose.
