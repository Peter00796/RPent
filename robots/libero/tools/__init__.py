"""LIBERO + OpenPI tool implementation, split by tool kind.

The agent-facing surface is native LangChain tools. Everything the planner reads
about a LIBERO tool comes from exactly two files:

- :mod:`.agent_tools` — the twelve ``@tool`` functions. **Each tool's description
  is its docstring.**
- :mod:`.schemas`     — Pydantic input models. **Each argument's description is
  its ``Field(description=...)``.**

Supporting the tool layer:

- :mod:`.context`     — ``LiberoContext``, delivered to tools via ``ToolRuntime``
- :mod:`.catalog`     — tool kinds + the advancing-primitive name set

Underneath, unchanged by the LangChain migration:

- :mod:`.primitives`  — the ``LiberoPrimitives`` core (env/policy handles, obs cache)
- :mod:`.motion`      — scripted OSC primitives (no VLM call)
- :mod:`.vla`         — Pi0.5 closed-loop primitives
- :mod:`.perception`  — SAM3 segmentation, calibration, back-projection handlers
- :mod:`.state`       — ``states.json`` dump/read, recipe export
- :mod:`.artifacts`   — the run-artifact path layout
- :mod:`.geometry`    — pure array/argument math (never agent-facing)

:mod:`.legacy_specs` renders the native tools back into Anthropic-shaped dicts
for the pre-LangChain planners; it is a migration shim, not a second source.
"""
from __future__ import annotations

from robots.libero.tools.agent_tools import (
    ADVANCING_TOOLS,
    LIBERO_TOOLS,
    MOTION_TOOLS,
    PERCEPTION_TOOLS,
    READ_ONLY_TOOLS,
    STATE_TOOLS,
    TOOLS_BY_KIND,
    VLA_TOOLS,
    back_project,
    move_pose,
    move_to,
    pi0_doubled,
    pi0_pick,
    plan_grasp,
    release,
    rotate_pitch,
    rotate_wrist,
    segment,
    set_gripper,
    view_camera_meta,
    view_driver_state,
)
from robots.libero.tools.artifacts import (
    ARTIFACT_DIRECTORIES,
    ARTIFACT_LAYOUT,
    artifact_path,
)
from robots.libero.tools.catalog import (
    MOTION,
    PERCEPTION,
    PRIMITIVE_TOOL_NAMES,
    STATE,
    VLA,
)
from robots.libero.tools.context import LiberoContext
from robots.libero.tools.legacy_specs import legacy_tool_specs
from robots.libero.tools.motion import MotionMixin
from robots.libero.tools.perception import SegmentMixin
from robots.libero.tools.primitives import LiberoPrimitives
from robots.libero.tools.state import dump_state, write_recipe_from_states
from robots.libero.tools.vla import VlaMixin

__all__ = [
    # agent-facing tools
    "LIBERO_TOOLS",
    "ADVANCING_TOOLS",
    "READ_ONLY_TOOLS",
    "STATE_TOOLS",
    "MOTION_TOOLS",
    "VLA_TOOLS",
    "PERCEPTION_TOOLS",
    "TOOLS_BY_KIND",
    "view_driver_state",
    "move_to",
    "move_pose",
    "rotate_wrist",
    "rotate_pitch",
    "release",
    "set_gripper",
    "pi0_pick",
    "pi0_doubled",
    "view_camera_meta",
    "segment",
    "back_project",
    # per-run context
    "LiberoContext",
    # kinds
    "STATE",
    "MOTION",
    "VLA",
    "PERCEPTION",
    "PRIMITIVE_TOOL_NAMES",
    # artifact layout
    "ARTIFACT_LAYOUT",
    "ARTIFACT_DIRECTORIES",
    "artifact_path",
    # primitives
    "LiberoPrimitives",
    "MotionMixin",
    "VlaMixin",
    "SegmentMixin",
    # state trace
    "dump_state",
    "write_recipe_from_states",
    # migration shim
    "legacy_tool_specs",
]
