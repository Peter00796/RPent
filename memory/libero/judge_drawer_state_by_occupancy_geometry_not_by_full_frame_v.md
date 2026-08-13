---
title: Judge drawer state by occupancy geometry, not by full-frame VLM claims
type: failure_mode
scope: env
conditions: When a drawer/cabinet-opening task is attempted; when the VLM narrates
  "open" or "closed" from full-frame images; when SAM is asked to segment a drawer
  handle.
support: 1
provenance:
- action: add
  proposal: logs/gate_gen0full_libero_10_task/proposals/proposal_08.md
  batch: gen0full_night
  date: '2026-08-14'
  evidence:
  - run:20260813-15:15:00_libero_10_task_t3_s0#seq=25
  - run:20260813-15:15:00_libero_10_task_t3_s0#seq=27
  - run:20260813-15:15:00_libero_10_task_t3_s0#seq=29
  - run:20260813-15:15:00_libero_10_task_t3_s0#seq=7
  - run:20260813-15:15:00_libero_10_task_t3_s0#seq=68
  - run:20260813-15:15:00_libero_10_task_t3_s0#seq=43
  - run:20260813-15:15:00_libero_10_task_t3_s0#seq=70
  counter_evidence: []
---

In drawer scenes, full-frame VLM state narration is not ground truth: it can claim an open cavity while a tight crop and occupancy agree the drawer is closed, and SAM handle segments can lock onto unrelated objects or the robot's own arm. Use occupancy scans of the drawer volume as the state oracle and as the handle-position check. If occupancy shows no protrusion past the front face, do not believe "open" or spend more skills on the handle.
