"""The ``inspect_image`` vision channel: a VLM as a measuring instrument.

The planner stays blind (``--no-images``); this module gives it an
INSTRUMENT, not eyes. One call sends one on-disk image — optionally cropped
to up to three regions — to a configured vision model and returns that
model's reply VERBATIM. The tool is a transparent pipe, by owner decision
(2026-08-11): no summarising, no filtering, no answer extraction, no
truncation of the reply; ``max_tokens`` is the VLM's generation budget, not
a post-hoc cut. In the reverse direction every piece of text the tool sends
is recorded in the result (``sent``), so what the intermediary did is
auditable from the run record alone — the answer side does nothing, and the
question side only adds mechanical crop labels.

Config mirrors the sandbox pattern: one run per process, ``configure()``
called by main.py from ``--vision-tool``; until then the tool answers with a
structured error. The model spec uses ``init_chat_model`` syntax
(``openai:glm-4.6v``, ``anthropic:claude-sonnet-4-6``), so swapping the
reader — the ablation arm — is one CLI argument.

The VLM request carries NO task context: a fixed one-line system message
and the planner's question. The reader answers about pixels; it does not
know what the task is, so it cannot smuggle task decisions past the planner.
"""
from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

from rpent.tools import sandbox

#: The entire system prompt the reader model gets. Fixed and task-blind.
SYSTEM_LINE = (
    "You are an image analyst for a robot. Answer the question about the "
    "image(s) concisely and directly; if you are not sure, say so "
    "explicitly."
)

MAX_REGIONS = 3

_CONFIG: dict[str, Any] | None = None
_CLIENT: Any = None


def configure(model_spec: str, *, base_url: str | None = None,
              max_tokens: int = 1000, client: Any = None) -> None:
    """Arm the vision channel for this run.

    ``client`` overrides the constructed chat model (tests only); otherwise
    the client is built lazily on first call so a bad spec fails inside a
    tool result, not at startup.
    """
    global _CONFIG, _CLIENT
    _CONFIG = {"model_spec": model_spec, "base_url": base_url,
               "max_tokens": max_tokens}
    _CLIENT = client


def clear() -> None:
    global _CONFIG, _CLIENT
    _CONFIG = None
    _CLIENT = None


def is_configured() -> bool:
    return _CONFIG is not None


def model_spec() -> str | None:
    return _CONFIG["model_spec"] if _CONFIG else None


def _client() -> Any:
    global _CLIENT
    if _CLIENT is None:
        from langchain.chat_models import init_chat_model

        kwargs: dict[str, Any] = {"max_tokens": _CONFIG["max_tokens"]}
        if _CONFIG["base_url"]:
            kwargs["base_url"] = _CONFIG["base_url"]
        _CLIENT = init_chat_model(_CONFIG["model_spec"], **kwargs)
    return _CLIENT


def _data_uri(png_bytes: bytes, media_type: str = "image/png") -> str:
    return f"data:{media_type};base64," + base64.b64encode(png_bytes).decode()


def _crop_blocks(path: Path, regions: list[list[int]]) -> tuple[list, list[str]]:
    """Render each region as a labeled crop block pair. Pixel ops only."""
    import imageio.v2 as imageio
    import numpy as np

    img = np.asarray(imageio.imread(path))
    h, w = img.shape[0], img.shape[1]
    blocks: list = []
    labels: list[str] = []
    for i, region in enumerate(regions, 1):
        r0, c0, r1, c1 = (int(v) for v in region)
        if not (0 <= r0 < r1 <= h and 0 <= c0 < c1 <= w):
            raise ValueError(
                f"region {i} {region} is outside the {h}x{w} image "
                "(need 0 <= r0 < r1 <= height, 0 <= c0 < c1 <= width)"
            )
        buf = io.BytesIO()
        imageio.imwrite(buf, img[r0:r1, c0:c1], format="png")
        label = f"Crop {i} = rows {r0}:{r1}, cols {c0}:{c1} of {path.name}"
        labels.append(label)
        blocks.append({"type": "text", "text": label})
        blocks.append({"type": "image_url",
                       "image_url": {"url": _data_uri(buf.getvalue())}})
    return blocks, labels


def _verbatim(content: Any) -> str:
    """Flatten a reply's content to text without altering the words."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("text") is not None:
                parts.append(str(block["text"]))
        return "\n".join(parts)
    return str(content)


def inspect_image(path: str, question: str,
                  regions: list[list[int]] | None = None) -> dict:
    """Ask the configured vision model one question about one image."""
    if _CONFIG is None:
        return {"error": "the vision channel is not configured for this run "
                         "(--vision-tool was not passed)"}
    file_path = Path(path)
    try:
        sandbox.check_read(file_path)
    except sandbox.SandboxDenied as denied:
        return denied.as_error()
    if not file_path.exists():
        return {"error": f"image not found: {file_path}"}
    if regions is not None and len(regions) > MAX_REGIONS:
        return {"error": f"at most {MAX_REGIONS} regions per call, "
                         f"got {len(regions)}"}

    import mimetypes

    labels: list[str] = []
    if regions:
        try:
            content, labels = _crop_blocks(file_path, regions)
        except ValueError as exc:
            return {"error": str(exc)}
        except Exception as exc:
            return {"error": f"could not crop {file_path}: {exc}"}
    else:
        media_type = mimetypes.guess_type(file_path.name)[0] or "image/png"
        content = [{"type": "image_url",
                    "image_url": {"url": _data_uri(file_path.read_bytes(),
                                                   media_type)}}]
    content.append({"type": "text", "text": question})

    try:
        reply = _client().invoke([
            {"role": "system", "content": SYSTEM_LINE},
            {"role": "user", "content": content},
        ])
    except Exception as exc:
        return {"error": f"vision model call failed: {type(exc).__name__}: "
                         f"{exc}"}

    usage = getattr(reply, "usage_metadata", None) or {}
    out: dict[str, Any] = {
        # The reply, verbatim. The tool is a transparent pipe — judging the
        # answer is the planner's job.
        "answer": _verbatim(reply.content),
        "model": _CONFIG["model_spec"],
        "path": str(file_path),
        "regions": regions,
        "sent": {"system": SYSTEM_LINE, "question": question,
                 "crop_labels": labels},
        "vlm_usage": {"in": usage.get("input_tokens"),
                      "out": usage.get("output_tokens")},
    }
    reasoning = (getattr(reply, "additional_kwargs", None) or {}).get(
        "reasoning_content")
    if reasoning:
        out["reasoning"] = str(reasoning)
    return out
