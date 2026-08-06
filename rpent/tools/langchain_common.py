"""The common file/IO tools as native LangChain tools.

Environment-independent counterpart of :mod:`robots.libero.tools.agent_tools`:
the handlers stay in :mod:`rpent.tools.common` (plain functions, callable without
a graph) and this module wraps them as ``@tool``. Descriptions are the
docstrings; argument descriptions are the ``Field(description=...)`` below.

``read_image`` exists in two variants under the same tool name — one that sends
image bytes and one that only acknowledges the path — so ``--no-images`` changes
what a text-only model receives without changing the tool surface it sees.
Pick with :func:`common_tools`.

⚠ Do not add ``from __future__ import annotations`` here. LangChain resolves a
``ToolRuntime`` parameter by its real annotation type; under PEP 563 detection
silently fails and the call dies at dispatch. No tool here needs ``runtime``
today, but keeping the rule uniform across ``@tool`` modules avoids a future
one-line change turning into a runtime-only failure.
"""

import base64
import mimetypes
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from rpent.tools import common

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


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

_READ_IMAGE_DESCRIPTION = (
    "Read a local image path returned by an RPent tool as visual input."
)

#: Under ``--no-images`` the tool cannot do what the normal description promises,
#: so it advertises the truth instead. Keeping the original wording would spend
#: the model's turns discovering that a described capability does not exist —
#: worse, in a single-attempt episode, than telling it up front. The tool is kept
#: rather than dropped because the system prompt still instructs image
#: inspection, so a call is likely and the result should redirect rather than
#: fail as an unknown tool.
_READ_IMAGE_TEXT_ONLY_DESCRIPTION = (
    "DISABLED in this run: image input is off (text-only model), so this tool "
    "cannot return visual content and looking at a PNG is not available to you. "
    "Localize objects instead with `segment` (SAM3 text prompt -> world_xyz) and "
    "`back_project`, and read state from `view_driver_state`."
)


@tool(args_schema=ReadTextFileInput)
def read_text_file(path: str, max_chars: int = 40000) -> dict:
    """Read a UTF-8 text file. Use for past recipe JSONLs, audit JSONs, and
    memory files. Large files are truncated.
    """
    return common.read_text_file(path, max_chars)


@tool(args_schema=WriteTextFileInput)
def write_text_file(path: str, content: str) -> dict:
    """Write a UTF-8 text file (creates parent dirs). Use this to save the
    working recipe JSONL and the final audit JSON at the end of a successful run.
    """
    return common.write_text_file(path, content)


@tool(args_schema=ListDirInput)
def list_dir(path: str = "") -> dict:
    """List files in a directory (non-recursive). Defaults to the run's output
    directory. Use to inspect the working directory or to discover existing
    recipes in resources/libero/results_*_pert/.
    """
    return common.list_dir(path)


@tool(args_schema=FinishInput)
def finish(status: str, summary: str) -> dict:
    """Call when the task is complete or unrecoverable. Halts the agent loop.
    Save any artifacts (recipe, audit) BEFORE calling finish.
    """
    return common.finish(status, summary)


@tool("read_image", args_schema=ReadImageInput, description=_READ_IMAGE_DESCRIPTION)
def read_image(path: str) -> list[dict[str, Any]] | str:
    """See ``_READ_IMAGE_DESCRIPTION`` — the model-facing text is passed
    explicitly so both variants advertise themselves identically.
    """
    file_path = Path(path)
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
    description=_READ_IMAGE_TEXT_ONLY_DESCRIPTION,
)
def read_image_text_only(path: str) -> str:
    """``read_image`` under ``--no-images``: redirect, send no bytes."""
    return (
        f"{path} exists, but image input is disabled (--no-images, text-only "
        "model), so its contents are not available to you. Localize with "
        "`segment` (SAM3 text prompt) and `back_project` instead, and read "
        "state from `view_driver_state`."
    )


def common_tools(*, no_images: bool = False) -> list[BaseTool]:
    """Return the environment-independent tools every planner gets.

    Args:
        no_images: Swap ``read_image`` for the byte-free variant. Both advertise
            the same name and description, so the model's tool surface is
            unchanged; only the result differs.
    """
    return [
        read_text_file,
        write_text_file,
        list_dir,
        finish,
        read_image_text_only if no_images else read_image,
    ]
