"""Common physical agent tools."""
from __future__ import annotations

import os
from pathlib import Path

from rpent.tools.tool_docs import render_description
from rpent.utils.config import get_repo_root
from rpent.utils.logging import get_output_dir

# Descriptions render from rpent/tools/tool_docs.py — edit them there, never
# inline. The native LangChain surface renders from the same source.
TOOLS_SPEC: list[dict] = [
    {
        "name": "read_text_file",
        "description": render_description("read_text_file"),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or repo-relative path"},
                "max_chars": {"type": "integer", "description": "Max chars (default 40000)"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_text_file",
        "description": render_description("write_text_file"),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_dir",
        "description": render_description("list_dir"),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Default: {{output_dir}}"},
            },
        },
    },
    {
        "name": "finish",
        "description": render_description("finish"),
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Outcome, e.g. 'success', 'failure', or 'stuck'.",
                },
                "summary": {
                    "type": "string",
                    "description": "Short natural-language summary of the run.",
                },
            },
            "required": ["status", "summary"],
        },
    },
]


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = get_repo_root() / p
    return p


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return (
        text[:max_chars]
        + f"\n\n[TRUNCATED — file is {len(text)} chars, showed first {max_chars}]"
    )


def read_text_file(path: str, max_chars: int = 40000) -> dict:
    p = _resolve(path)
    if not p.exists():
        return {"error": f"file not found: {p}"}
    if p.is_dir():
        return {"error": f"is a directory: {p}"}
    try:
        text = p.read_text(errors="replace")
    except Exception as e:
        return {"error": str(e)}
    return {"path": str(p), "size": len(text), "content": _truncate(text, max_chars)}


def write_text_file(path: str, content: str) -> dict:
    p = _resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return {"path": str(p), "bytes_written": len(content.encode("utf-8"))}


def list_dir(path: str = "") -> dict:
    # Default to the current output dir (so parallel agents see their own).
    p = _resolve(path) if path else get_output_dir()
    if not p.exists():
        return {"error": f"directory not found: {p}"}
    files = sorted(os.listdir(p))
    return {"path": str(p), "count": len(files), "files": files}


def finish(status: str, summary: str) -> dict:
    """Signal that the run is complete. Halts the agent loop.

    The ``_finish`` sentinel is what each planner detects to stop the
    tool-calling loop — see ``event.part.tool_name == "finish"`` in
    :meth:`rpent.planner.api_loop.ApiAgentLoop._solve` and the
    ``pending_finish`` bookkeeping in
    :class:`rpent.planner.claude_code._Recorder`.
    """
    return {"_finish": True, "status": status, "summary": summary}


TOOL_HANDLERS: dict = {
    "read_text_file": read_text_file,
    "write_text_file": write_text_file,
    "list_dir": list_dir,
    "finish": finish,
}
