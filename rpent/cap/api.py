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
import time
from typing import Any

from rpent.tools import tool_log

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


def instrument(name: str, fn, ctx: Any, output_dir) -> Any:
    """Wrap one API function so its calls land in ``tool_calls.jsonl``.

    Found the hard way on the first smoke run: the tool-call log is written
    by a LANGCHAIN middleware, so program runs — which never build a graph —
    advanced 23 env steps while recording ZERO calls, and the coding agent
    debugged nearly blind. For program runs, THIS wrapper is the uniform
    seam the middleware provides for tool runs; without it the evidence
    inheritance the CaP arm is built on is a false promise.
    """
    def wrapped(**kwargs):
        before = getattr(ctx, "step_idx", None)
        start = time.monotonic()
        try:
            result = fn(**kwargs)
        except ProgramHalt:
            raise  # finish() is control flow, not a tool call outcome
        except Exception as exc:
            tool_log.append(
                output_dir, tool=name, args=kwargs,
                result={"error": f"{type(exc).__name__}: {exc}"},
                elapsed_s=time.monotonic() - start,
                step_idx_before=before,
                step_idx_after=getattr(ctx, "step_idx", None),
                status="raised",
            )
            raise
        tool_log.append(
            output_dir, tool=name, args=kwargs, result=result,
            elapsed_s=time.monotonic() - start,
            step_idx_before=before,
            step_idx_after=getattr(ctx, "step_idx", None),
        )
        return result
    wrapped.__name__ = name
    return wrapped


def make_api(ctx: Any, output_dir=None) -> dict[str, Any]:
    """Build the callable namespace for one run's program.

    ``ctx`` is the run's :class:`LiberoContext`. Env-advancing calls go
    through ``ctx.advance`` (bookkeeping identical to the tool path);
    read-only calls hit the same handler modules the tools wrap. When
    ``output_dir`` is given, every call is instrumented into
    ``tool_calls.jsonl`` — program runs must leave the same evidence trail
    tool runs do.
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

    if output_dir is not None:
        api = {name: instrument(name, fn, ctx, output_dir)
               for name, fn in api.items()}

    def finish(status: str, summary: str):
        raise ProgramHalt(status, summary)

    api["finish"] = finish
    return api


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    """Allow ``import math`` / ``import json`` — and nothing else.

    The first smoke run died on ``import math`` even though ``math`` was
    already a global: models write the import line reflexively, and failing
    a whole episode over a no-op statement is discipline where a mechanism
    is cheap. Anything beyond the two whitelisted modules still raises.
    """
    if name in ("math", "json"):
        return {"math": math, "json": json}[name]
    raise ImportError(
        f"import of {name!r} is not available to programs; the API functions, "
        "math and json are the whole toolbox"
    )


def exec_namespace(api: dict[str, Any]) -> dict[str, Any]:
    """The globals a program executes under: API + a small safe prelude."""
    safe_builtins = {name: getattr(builtins, name) for name in _SAFE_BUILTIN_NAMES
                     if hasattr(builtins, name)}
    safe_builtins["True"], safe_builtins["False"], safe_builtins["None"] = True, False, None
    safe_builtins["__import__"] = _safe_import
    return {
        "__builtins__": safe_builtins,
        "math": math,
        "json": json,
        **api,
    }
