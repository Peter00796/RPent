---
title: Localise the butter by low-slab elimination, not by name
type: technique
scope: task
conditions: t6 only; whenever the butter (or any low flat target) fails name prompts
support: 1
provenance:
- action: add
  proposal: logs/playbook_t6/proposals/butter_localisation.md
  batch: playbook_t6
  date: '2026-08-11'
  evidence:
  - run:20260811-05:27:15_libero_object_swap_t6_s51#seq=11
  - run:20260811-05:27:15_libero_object_swap_t6_s51#seq=12
  - run:20260811-05:27:15_libero_object_swap_t6_s51#seq=13
  - run:20260811-05:27:15_libero_object_swap_t6_s51#seq=24
  - run:20260811-05:27:15_libero_object_swap_t6_s51#seq=26
  - run:20260811-05:27:15_libero_object_swap_t6_s51#seq=29
  counter_evidence: []
---

Name and colour prompts do NOT localise the butter here (colour phrasings latch
onto the orange-juice carton). The recipe that works, all values relative to the
measured table plane (table_z = min z of object clusters):

1. ENUMERATE the namable objects (basket, bottles, cartons) with segment and
   register each; note which clusters they claim.
2. LOW-Z SWEEP: back_project unclaimed image regions with a z band of
   [table_z + 0.005, table_z + 0.05]; the butter shows up as an UNCLAIMED flat
   cluster with median z about 1.5-2 cm above the table.
3. RAISED-SLAB TEST (the discriminator): world_extent occupancy in z band
   [table_z + 0.008, table_z + 0.035] over each low candidate. The butter
   signature: footprint about 0.07 x 0.05 m, height about 0.017 m, FLAT top
   (z-profile spread under 5 mm). Table noise returns near-zero voxels.
4. IDENTITY BY ELIMINATION: every other named object answers some prompt and
   owns its cluster; the unclaimed flat slab is the butter. Even the failed
   'butter' prompt's rejected box points at the same image region.
Grasp note: fingers span the short axis (about 0.05 m); descend to about
table_z + 0.025-0.03 before closing; expect the flat-low-profile air-grasp
failure mode (see the common library entry) if closing beside the slab.
