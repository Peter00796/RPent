"""The common file/IO tools as native LangChain tools.

Environment-independent counterpart of :mod:`robots.libero.tools.agent_tools`:
the handlers stay in :mod:`rpent.tools.common` (plain functions, callable without
a graph) and this module wraps them as ``@tool``. Model-facing descriptions
render from the structured entries in :mod:`rpent.tools.tool_docs` (docstrings
here are developer notes only); argument descriptions are the
``Field(description=...)`` below.

``read_image`` exists in two variants under the same tool name — one that sends
image bytes and one that only acknowledges the path — so ``--no-images`` changes
what a text-only model receives without changing the tool names it sees.
Pick with :func:`common_tools`.

⚠ Do not add ``from __future__ import annotations`` here. LangChain resolves a
``ToolRuntime`` parameter by its real annotation type; under PEP 563 detection
silently fails and the call dies at dispatch. No tool here needs ``runtime``
today, but keeping the rule uniform across ``@tool`` modules avoids a future
one-line change turning into a runtime-only failure.
"""

import base64
import json
import mimetypes
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from rpent.tools import common, sandbox
from rpent.tools.tool_docs import render_description

# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------


class ReadTextFileInput(BaseModel):
    """Which text file to read, and how much of it."""

    path: str = Field(description="Absolute or repo-relative path")
    max_chars: int = Field(default=40000, description="Max chars (default 40000)")


class WriteTextFileInput(BaseModel):
    """Where to write, and what."""

    path: str = Field(description="Absolute or repo-relative path")
    content: str = Field(description="Full UTF-8 file contents to write")


class ListDirInput(BaseModel):
    """Which directory to list."""

    path: str = Field(default="", description="Default: the run's output directory")


class FinishInput(BaseModel):
    """The run's outcome."""

    status: str = Field(
        description="Outcome, e.g. 'success', 'failure', or 'stuck'.",
    )
    summary: str = Field(
        description="Short natural-language summary of the run.",
    )


class ReadImageInput(BaseModel):
    """Which image file to read as visual input."""

    path: str = Field(description="Path to a local image file")


class ViewAttemptCallInput(BaseModel):
    """Which archived tool call to retrieve."""

    attempt: int = Field(
        ge=1, description="Archived attempt number (the N in attempt_NN/)"
    )
    seq: int = Field(
        ge=1, description="Call sequence number within that attempt's log"
    )


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool(args_schema=ReadTextFileInput, description=render_description("read_text_file"))
def read_text_file(path: str, max_chars: int = 40000) -> dict:
    """Model-facing text renders from ``tool_docs`` — edit it there."""
    return common.read_text_file(path, max_chars)


@tool(args_schema=WriteTextFileInput, description=render_description("write_text_file"))
def write_text_file(path: str, content: str) -> dict:
    """Model-facing text renders from ``tool_docs`` — edit it there."""
    return common.write_text_file(path, content)


@tool(args_schema=ListDirInput, description=render_description("list_dir"))
def list_dir(path: str = "") -> dict:
    """Model-facing text renders from ``tool_docs`` — edit it there."""
    return common.list_dir(path)


@tool(args_schema=FinishInput, description=render_description("finish"))
def finish(status: str, summary: str) -> dict:
    """Model-facing text renders from ``tool_docs`` — edit it there."""
    return common.finish(status, summary)


@tool(
    "read_image",
    args_schema=ReadImageInput,
    description=render_description("read_image"),
)
def read_image(path: str) -> list[dict[str, Any]] | str:
    """Model-facing text renders from ``tool_docs`` — edit it there.

    Sandboxed like every other read: without the check this would be a
    generic byte-exfiltration channel (any file, base64, straight to the
    model), not just an image viewer.
    """
    file_path = Path(path)
    try:
        sandbox.check_read(file_path)
    except sandbox.SandboxDenied as denied:
        return json.dumps(denied.as_error())
    if not file_path.exists():
        return f"image not found: {path}"
    media_type = mimetypes.guess_type(file_path.name)[0] or "image/png"
    return [
        {"type": "text", "text": path},
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.b64encode(file_path.read_bytes()).decode("utf-8"),
            },
        },
    ]


@tool(
    "read_image",
    args_schema=ReadImageInput,
    description=render_description("read_image_text_only"),
)
def read_image_text_only(path: str) -> str:
    """``read_image`` under ``--no-images``: redirect, send no bytes. The
    rationale for the honest variant lives with its docs entry in ``tool_docs``.
    """
    return (
        f"{path} exists, but image input is disabled (--no-images, text-only "
        "model), so its contents are not available to you. Localize with "
        "`segment` (SAM3 text prompt) and `back_project` instead, and read "
        "state from `view_driver_state`."
    )


@tool(
    args_schema=ViewAttemptCallInput,
    description=render_description("view_attempt_call"),
)
def view_attempt_call(attempt: int, seq: int) -> dict:
    """Model-facing text renders from ``tool_docs`` — edit it there."""
    return common.view_attempt_call(attempt, seq)


def common_tools(*, no_images: bool = False,
                 resident: bool = False) -> list[BaseTool]:
    """Return the environment-independent tools every planner gets.

    Args:
        no_images: Swap ``read_image`` for the byte-free variant. Both expose
            the same name and schema; the text-only variant advertises the
            truth (no visual content available) and sends no bytes.
        resident: Add ``view_attempt_call``, the drill-down into archived
            attempts. Exists only in resident debug sessions — exam runs have
            no attempts to drill into, and not shipping the tool is the
            mechanism form of that statement.
    """
    tools = [
        read_text_file,
        write_text_file,
        list_dir,
        finish,
        read_image_text_only if no_images else read_image,
    ]
    if resident:
        tools.append(view_attempt_call)
    return tools
