---
title: Retry failed Pi0 picks from a clear/home viewpoint before giving up
type: technique
scope: common
conditions: Applies when repeated close-range pi0_pick attempts end with holding=false
  or drift off target.
support: 1
provenance:
- action: add
  proposal: logs/gate_gen1/proposals/proposal_05.md
  batch: gate_gen1
  date: '2026-08-07'
  evidence:
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=28
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=33
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=43
  - run:20260807-15:39:36_libero_object_swap_t7_s0#seq=44
  counter_evidence:
  - run:20260807-16:08:47_libero_object_swap_t9_s0#seq=59
---

If pi0 fails while the arm is close to the object, wall, or container, repeating the same configuration tends to repeat the same failure. Retreat to a clear or home viewpoint and issue a fresh pick from there. If that retry also fails, stop the pi0 ladder. Always verify with held-object geometry before continuing.
---
