"""The Python API a generated program sees: the tool layer, bound to a run.

One function per tool, same names, same argument names as the tool schemas —
the API documentation IS the rendered tool_docs, so a program author (human
or model) reads the same contract the turn-by-turn planner reads.

Every advancing call routes through ``ctx.advance`` and every read-only call
through the same handlers the tools use, so the evidence trail
(``tool_calls.jsonl``, states, the databus, sandbox enforcement) is identical
whichever policy form drives the run. That equivalence is the point: the
CaP arm and the tool-loop arm differ ONLY in who decides the next call.

The execution namespace is deliberately small: the API functions, a few safe
builtins, ``math``/``json``, and no ``__import__``. A program that needs more
than the primitives is a program asking to escape the experiment.
"""
from __future__ import annotations

import builtins
import json
import math
from typing import Any

#: Builtins a program may use. No __import__, no open, no exec/eval/compile.
_SAFE_BUILTIN_NAMES = (
    "abs", "all", "any", "bool", "dict", "enumerate", "float", "int", "len",
    "list", "max", "min", "print", "range", "reversed", "round", "set",
    "sorted", "str", "sum", "tuple", "zip", "True", "False", "None",
    "Exception", "ValueError", "RuntimeError", "isinstance", "repr",
)


class ProgramHalt(Exception):
    """Raised by ``finish()`` inside a program to end the episode cleanly."""

    def __init__(self, status: str, summary: str):
        super().__init__(f"{status}: {summary}")
        self.result = {"_finish": True, "status": status, "summary": summary}


def make_api(ctx: Any) -> dict[str, Any]:
    """Build the callable namespace for one run's program.

    ``ctx`` is the run's :class:`LiberoContext`. Env-advancing calls go
    through ``ctx.advance`` (bookkeeping + logging identical to the tool
    path); read-only calls hit the same handler modules the tools wrap.
    """
    from robots.libero.tools import geometry, perception, state

    prims = ctx.primitives

    def _adv(name: str, primitive, **kwargs):
        return ctx.advance(name, kwargs, primitive)

    api: dict[str, Any] = {
        # -- state ----------------------------------------------------------
        "view_driver_state": lambda step=None: state.view_driver_state(step),
        # -- motion ----------------------------------------------------------
        "move_to": lambda **kw: _adv("move_to", prims.move_to, **kw),
        "move_pose": lambda **kw: _adv("move_pose", prims.move_pose, **kw),
        "rotate_wrist": lambda **kw: _adv("rotate_wrist", prims.rotate_wrist, **kw),
        "rotate_pitch": lambda **kw: _adv("rotate_pitch", prims.rotate_pitch, **kw),
        "release": lambda **kw: _adv("release", prims.release, **kw),
        "set_gripper": lambda **kw: _adv("set_gripper", prims.set_gripper, **kw),
        # -- vla ---------------------------------------------------------------
        "pi0_pick": lambda **kw: _adv("pi0_pick", prims.pi0_pick, **kw),
        "pi0_doubled": lambda **kw: _adv("pi0_doubled", prims.pi0_doubled, **kw),
        # -- perception ---------------------------------------------------------
        "view_camera_meta": lambda camera="agentview", step=None:
            perception.view_camera_meta(camera, step),
        "segment": lambda **kw: ctx.primitives.segment(**kw),
        "back_project": lambda **kw: perception.back_project(**kw),
        "world_extent": lambda **kw: geometry.world_extent(**kw),
        "compare_extent": lambda **kw: geometry.compare_extent(**kw),
    }

    def finish(status: str, summary: str):
        raise ProgramHalt(status, summary)

    api["finish"] = finish
    return api


def exec_namespace(api: dict[str, Any]) -> dict[str, Any]:
    """The globals a program executes under: API + a small safe prelude."""
    safe_builtins = {name: getattr(builtins, name) for name in _SAFE_BUILTIN_NAMES
                     if hasattr(builtins, name)}
    safe_builtins["True"], safe_builtins["False"], safe_builtins["None"] = True, False, None
    return {
        "__builtins__": safe_builtins,
        "math": math,
        "json": json,
        **api,
    }
