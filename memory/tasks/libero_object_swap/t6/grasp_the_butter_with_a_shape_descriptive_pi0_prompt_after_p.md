---
title: Grasp the butter with a shape-descriptive pi0 prompt after playbook localisation
type: technique
scope: task
conditions: after the butter is localised by the low-slab recipe; grasp phase
support: 1
provenance:
- action: add
  proposal: logs/playbook_t6b/proposals/grasp_prompt.md
  batch: playbook_t6b
  date: '2026-08-11'
  evidence:
  - run:20260811-06:20:22_libero_object_swap_t6_s52#seq=32
  - run:20260811-06:20:22_libero_object_swap_t6_s52#seq=35
  - run:20260811-06:20:22_libero_object_swap_t6_s52#step=2
  counter_evidence: []
---

Contrast pair from the controlled grasp experiment (same scene, one variable
changed): the name-only pi0 prompt failed the grasp; the SHAPE-DESCRIPTIVE
prompt 'pick up the flat butter slab' succeeded end-to-end — pi0 grasped the
low slab and the episode terminated during the same call. Recipe: localise
via the low-slab elimination entry first, then issue pi0_pick with a prompt
that names the shape ('flat ... slab'), not just the object name. Verify the
hold geometrically as usual; if the episode reports termination during the
pick, stop and finish — do not keep issuing motions.
