"""Tool kinds and the set of environment-advancing tool names.

The schemas moved to :mod:`robots.libero.tools.schemas` (Pydantic) and the tools
themselves to :mod:`robots.libero.tools.agent_tools`. What remains here is the
small, dependency-free vocabulary that other modules need without importing the
tool layer — notably the recipe exporter, which must know which logged commands
were real primitives.

This module imports nothing from the package, so it can never take part in an
import cycle.
"""
from __future__ import annotations

#: Tool kinds. ``motion`` and ``vla`` advance the environment; ``state`` and
#: ``perception`` are read-only over already-dumped artifacts.
STATE = "state"
MOTION = "motion"
VLA = "vla"
PERCEPTION = "perception"

#: Environment-advancing primitives. ``agent_tools`` asserts at import that this
#: matches its own ``ADVANCING_TOOLS`` list, so the two cannot drift.
PRIMITIVE_TOOL_NAMES: tuple[str, ...] = (
    "move_to",
    "pi0_pick",
    "pi0_doubled",
    "release",
    "set_gripper",
    "rotate_wrist",
    "rotate_pitch",
    "move_pose",
)
