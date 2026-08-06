"""The entity databus: named, append-only geometry readings with staleness.

A ``segment`` call produces one reading of one entity. Nothing here stores a
mutable "current position": readings are appended and never rewritten, so a
motion command can always cite the exact reading it was planned from, and a
later fusion of several viewpoints is a *computation over readings* that yields
another reading — not an in-place update that destroys its own inputs.

Averaging is deliberately not offered. For a hollow container the per-axis median
already sits on the near wall, so two readings taken from different angles have
biases that may cancel — but two readings that caught *different parts* of an
object (body vs cap) average to a point on neither. A reducer has to know what it
is reducing, so reduction stays an explicit tool, not a property of storage.

The heavy data stays where it already is: each reading points at the segment
artifact and the ``(H, W, 3)`` world map it came from. This file is an index over
those, small enough to ride along in a tool result.

Staleness is computed by the harness and interpreted by the planner. The harness
can say "the end-effector passed within 6 cm of where you last saw this"; only the
planner can decide whether that matters for the next command.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

import numpy as np

from robots.libero.tools.artifacts import artifact_path

SCHEMA_VERSION = 1

#: Default radius, in metres, within which end-effector motion makes a reading
#: suspect. Deliberately generous: a false ``possibly_bumped`` costs one
#: re-``segment``, while a missed one can cost the episode.
BUMP_RADIUS_M = 0.06

#: Two differently-named entities closer than this are probably one object read
#: twice. Tabletop objects measured 6-20 cm apart on real scenes, and a single
#: object's readings agreed to millimetres, so 3 cm separates the two cases with
#: room to spare.
COLLISION_RADIUS_M = 0.03

#: Staleness verdicts, ordered from most to least trustworthy.
FRESH = "fresh"
UNVERIFIED = "unverified"
POSSIBLY_BUMPED = "possibly_bumped"
HELD = "held"

#: A turn's tool calls execute concurrently in this process, so two ``segment``
#: calls can append at the same moment. A plain read-modify-write would lose one
#: of them. The writers are threads in one process, so a module lock is the whole
#: fix — no file locking needed.
_LOCK = threading.Lock()


def _path(output_dir: str | os.PathLike[str]) -> Path:
    return artifact_path(output_dir, "entities")


def load(output_dir: str | os.PathLike[str]) -> dict[str, list[dict[str, Any]]]:
    """Return ``{entity: [reading, ...]}``, oldest reading first. Empty if none."""
    path = _path(output_dir)
    if not path.exists():
        return {}
    try:
        blob = json.loads(path.read_text())
    except Exception:
        return {}
    entities = blob.get("entities")
    return entities if isinstance(entities, dict) else {}


def _save(output_dir: str | os.PathLike[str], entities: dict) -> None:
    """Write the index atomically, so a concurrent reader never sees a partial file."""
    path = _path(output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps({"schema_version": SCHEMA_VERSION, "entities": entities}, indent=2)
    )
    os.replace(tmp, path)


def append_reading(
    output_dir: str | os.PathLike[str],
    entity: str,
    reading: dict[str, Any],
) -> dict[str, Any]:
    """Append one reading of ``entity`` and report how it relates to the last one.

    Returns a small dict for the caller to surface to the planner:
    ``n_readings``, and — when a previous reading exists — ``moved_since_last_m``
    plus an ``identity_warning`` if that distance is large.

    The distance check is the one guard against the failure the task prompt calls
    unrecoverable: two identical objects in a scene carry no perceptual
    difference in their names, so a planner that re-segments "the black bowl" can
    silently bind the *other* bowl to an entity it already registered. The
    harness cannot resolve which is right — only the planner knows whether the
    object was supposed to have moved — so it reports the tension instead of
    guessing.
    """
    entity = (entity or "").strip()
    if not entity:
        return {}
    with _LOCK:
        entities = load(output_dir)
        history = entities.setdefault(entity, [])
        info: dict[str, Any] = {"entity": entity, "n_readings": len(history) + 1}

        previous = None
        for candidate in reversed(history):
            if candidate.get("world_xyz"):
                previous = candidate
                break
        here = reading.get("world_xyz")
        if previous is not None and here:
            delta = float(
                np.linalg.norm(
                    np.asarray(here, dtype=np.float64)[:3]
                    - np.asarray(previous["world_xyz"], dtype=np.float64)[:3]
                )
            )
            info["moved_since_last_m"] = round(delta, 4)
            info["previous_step"] = previous.get("step")
            info["previous_stale_reason"] = previous.get("stale_reason")
            if delta > 0.05 and previous.get("stale_reason") in (FRESH, UNVERIFIED):
                info["identity_warning"] = (
                    f"this reading is {delta:.3f} m from the last one of "
                    f"'{entity}' (step {previous.get('step')}), which nothing had "
                    "marked as bumped — either the object moved, or this mask is "
                    "a different object with the same appearance. Resolve before "
                    "committing a grasp."
                )

        # Cross-entity collision. Two DIFFERENT names landing on the same place
        # means the segmentation did not distinguish them, so at most one label is
        # right — and unlike a within-entity jump, no amount of re-reading the same
        # noun will surface it, because each reading is individually consistent.
        # Note the limit: this catches a collision, not a swap. Two entities at two
        # distinct positions with their labels exchanged are geometrically
        # self-consistent, and no measurement here can separate them; that needs
        # corroboration from an independently-phrased query.
        if here:
            for other, other_history in entities.items():
                if other == entity:
                    continue
                latest = next(
                    (r for r in reversed(other_history) if r.get("world_xyz")), None
                )
                if latest is None:
                    continue
                gap = float(
                    np.linalg.norm(
                        np.asarray(here, dtype=np.float64)[:3]
                        - np.asarray(latest["world_xyz"], dtype=np.float64)[:3]
                    )
                )
                if gap <= COLLISION_RADIUS_M:
                    info["collision_with"] = other
                    info["collision_gap_m"] = round(gap, 4)
                    info["collision_warning"] = (
                        f"'{entity}' and '{other}' are only {gap:.3f} m apart, close "
                        "enough to be the same object read twice under two names. "
                        "The segmentation did not separate them, so at most one "
                        "label is correct. Corroborate with a differently-phrased "
                        "query — a discriminating attribute rather than the name — "
                        "and check it lands on the same reading before committing "
                        "a grasp."
                    )
                    break

        reading = dict(reading)
        reading.setdefault("stale_reason", FRESH)
        history.append(reading)
        _save(output_dir, entities)
    return info


def mark_after_motion(
    output_dir: str | os.PathLike[str],
    *,
    eef_before: Any,
    eef_after: Any,
    gripper_open: bool,
    radius: float = BUMP_RADIUS_M,
) -> None:
    """Downgrade every reading's staleness after one environment-advancing action.

    A reading taken before a motion is no longer *verified*, whichever way the arm
    went; whether it is likely *wrong* depends on how close the end-effector came.

    - ``possibly_bumped`` — the end-effector came within ``radius``
    - ``unverified``      — the world changed but the arm stayed away
    - ``held``            — the gripper is closed near the reading, so this entity
      is probably in hand and its world xyz is meaningless; use
      ``world_extent(mode="held_object")`` for the offset instead

    ⚠ Approximation: only the end-effector poses before and after the action are
    known here, and proximity is tested against the straight segment between them.
    The real path can bow away from that line — ``pi0_pick`` descends and lifts
    back to nearly the same point, so its descent is invisible to this test. The
    verdict is therefore a lower bound on disturbance: ``unverified`` means "not
    known to have been disturbed", never "known to be untouched".
    """
    try:
        a = np.asarray(eef_before, dtype=np.float64)[:3]
        b = np.asarray(eef_after, dtype=np.float64)[:3]
    except Exception:
        return
    with _LOCK:
        entities = load(output_dir)
        if not entities:
            return
        changed = False
        for history in entities.values():
            for reading in history:
                xyz = reading.get("world_xyz")
                if not xyz:
                    continue
                if reading.get("stale_reason") == HELD:
                    continue
                distance = _distance_to_segment(
                    np.asarray(xyz, dtype=np.float64)[:3], a, b
                )
                if distance <= radius and not gripper_open:
                    verdict, detail = HELD, (
                        f"gripper closed within {distance:.3f} m of this reading; "
                        "its world xyz is likely obsolete — query "
                        "world_extent(mode='held_object') for the eef offset"
                    )
                elif distance <= radius:
                    verdict, detail = POSSIBLY_BUMPED, (
                        f"end-effector passed within {distance:.3f} m of this "
                        "reading; re-segment before relying on it"
                    )
                else:
                    verdict, detail = UNVERIFIED, (
                        f"the world changed while the end-effector stayed "
                        f"{distance:.3f} m away; not known to be disturbed, but "
                        "no longer verified"
                    )
                if reading.get("stale_reason") != verdict:
                    changed = True
                reading["stale_reason"] = verdict
                reading["stale_detail"] = detail
        if changed:
            _save(output_dir, entities)


def index(output_dir: str | os.PathLike[str]) -> dict[str, Any] | None:
    """Return the compact per-entity summary that rides along in tool results.

    One row per entity: its newest reading with a world position, that reading's
    staleness, and how many readings exist. Returns ``None`` when nothing has
    been registered, so the caller can omit the field entirely rather than
    advertise an empty databus every turn.
    """
    entities = load(output_dir)
    if not entities:
        return None
    rows: dict[str, Any] = {}
    for entity, history in entities.items():
        latest = None
        for candidate in reversed(history):
            if candidate.get("world_xyz"):
                latest = candidate
                break
        latest = latest or (history[-1] if history else None)
        if latest is None:
            continue
        rows[entity] = {
            "world_xyz": latest.get("world_xyz"),
            "step": latest.get("step"),
            "camera": latest.get("camera"),
            "prompt": latest.get("prompt"),
            "score": latest.get("score"),
            "stale_reason": latest.get("stale_reason"),
            "stale_detail": latest.get("stale_detail"),
            "segment_path": latest.get("segment_path"),
            "n_readings": len(history),
        }
    if not rows:
        return None
    return {
        "note": (
            "Readings you registered with segment(entity=...). Append-only: a new "
            "segment adds a reading, it never overwrites one. stale_reason says "
            "how much to trust the position — re-segment anything not 'fresh' "
            "before committing a motion to it."
        ),
        "entities": rows,
    }


def _distance_to_segment(
    point: np.ndarray, start: np.ndarray, end: np.ndarray
) -> float:
    """Shortest distance from ``point`` to the segment ``start``-``end``."""
    span = end - start
    length_sq = float(span @ span)
    if length_sq < 1e-12:
        return float(np.linalg.norm(point - start))
    t = float(np.clip((point - start) @ span / length_sq, 0.0, 1.0))
    return float(np.linalg.norm(point - (start + t * span)))
