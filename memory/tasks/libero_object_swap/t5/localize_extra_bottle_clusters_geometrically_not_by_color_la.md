---
title: Localize extra bottle clusters geometrically, not by color-language segmentation
type: technique
scope: task
conditions: When localizing the tomato-sauce bottle after a pick attempt or when language
  segmentation and pixel queries are being used.
support: 1
provenance:
- action: add
  proposal: /mnt/user_dir/pengyanxin/rpent_refactor/logs/resident_libero_object_swap_t5/mine_00_old/proposals/proposal_04.md
  batch: mine_00_old
  date: '2026-08-11'
  evidence:
  - run:20260811-06:29:45_libero_object_swap_t5_s53#seq=19
  - run:20260811-06:29:45_libero_object_swap_t5_s53#seq=24
  - run:20260811-06:29:45_libero_object_swap_t5_s53#seq=33
  - run:20260811-06:29:45_libero_object_swap_t5_s53#seq=44
  - run:20260811-06:29:45_libero_object_swap_t5_s53#seq=47
  counter_evidence: []
- action: revise
  proposal: logs/resident_libero_object_swap_t5/mine_02_vision/proposals/proposal_02_owner_edit.md
  batch: resident_mine_02
  date: '2026-08-11'
  evidence:
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=7
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=8
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=19
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=20
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=22
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=10
  - run:20260811-20:48:01_libero_object_swap_t5_s51#seq=25
  counter_evidence: []
---

VLM pixel centers need a HEIGHT sanity check before use: back_project the
pixel and require the returned z to sit near table level for a tabletop
object. In this session the same channel both rescued a lost bottle
(pixel -> z=0.030, at table level, re-pick succeeded — archived attempt 2)
and misfired twice (pixels back-projected to z~0.13, the milk carton's
height; the VLM later described the same view as centered on the milk
carton with no bottle visible). A failed check means the VLM looked at the
wrong object: re-ask with a cropped region or fall back to geometric
elimination — do not command a motion from an unvalidated pixel. Also, one
zero-count occupancy box does not prove the object is absent: the identical
box returned 0 points at one step and thousands later, after motion. Use
occupancy checks spanning tabletop to bottle height and trust the latest
scan after any pick or movement.
