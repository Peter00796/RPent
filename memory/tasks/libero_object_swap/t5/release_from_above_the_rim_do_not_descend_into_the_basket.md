---
title: Release from above the rim with the gripper still closed; do not descend into
  the basket first
type: technique
scope: task
conditions: bottle verified held and carried to the basket; release phase
support: 1
provenance:
- action: add
  proposal: logs/resident_libero_object_swap_t5/mine_02_vision/proposals/proposal_03_release_recipe.md
  batch: resident_mine_02
  date: '2026-08-11'
  evidence:
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=41
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=42
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=74
  counter_evidence:
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=42
---

Carry the bottle above the basket and release from ABOVE the rim plane
(eef z ~= 0.25 with the rim at ~0.10) with the gripper still closed until
the pose is reached. Do not descend the eef into the basket interior
before opening: in this session the interior-release placement left the
bottle physically inside with the flag never firing, while the above-rim
drop fired it. The checker on this cell is flaky (one above-rim repeat
also failed to fire): after an above-rim release, check the interior
occupancy once; if the flag has not fired, write the honest audit and
stop — do not keep re-placing a bottle that is already in the basket.
