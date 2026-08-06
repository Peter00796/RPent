"""Migration shim: Anthropic-shaped tool schemas derived from the native tools.

The ``api`` / ``claude_code`` / ``codex`` planners consume
``{"name", "description", "input_schema"}`` dicts through
:class:`~rpent.tools.toolkit.Toolkit`. Those schemas are no longer authored —
they are rendered from :data:`robots.libero.tools.agent_tools.LIBERO_TOOLS`, so
the LangChain tools stay the single source of truth and the two surfaces cannot
drift.

Only schemas are derived. Dispatch is untouched: ``LiberoToolkit`` already binds
its own handlers straight onto the primitives, so nothing here re-implements a
call path.

Delete this module once the LangChain planner is the only planner.
"""
from __future__ import annotations

from typing import Any

from langchain_core.utils.function_calling import convert_to_openai_tool

from robots.libero.tools.agent_tools import LIBERO_TOOLS


def legacy_tool_specs() -> list[dict[str, Any]]:
    """Render the native tools as Anthropic-shaped schema dicts."""
    specs: list[dict[str, Any]] = []
    for tool in LIBERO_TOOLS:
        rendered = convert_to_openai_tool(tool)["function"]
        specs.append(
            {
                "name": rendered["name"],
                "description": rendered.get("description", ""),
                "input_schema": rendered.get(
                    "parameters", {"type": "object", "properties": {}}
                ),
            }
        )
    return specs
