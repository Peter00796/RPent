"""Minimal markdown for the planner's reasoning text.

The model writes **bold**, `code` and bullet lists; showing that raw as
pre-wrapped text is unreadable. This renders exactly those three forms plus
paragraphs — nothing more — with escaping first, so the output is safe to
inject. Not a markdown engine on purpose: reasoning is evidence, and an
ambitious renderer that reflows it starts editing the record.
"""
from __future__ import annotations

import html
import re


def render_markdown(text: str) -> str:
    escaped = html.escape(str(text))
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", escaped)

    out: list[str] = []
    in_list = False
    for line in escaped.split("\n"):
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")) or re.match(r"^\d+[.)] ", stripped):
            if not in_list:
                out.append("<ul>")
                in_list = True
            item = re.sub(r"^(?:[-*]|\d+[.)])\s+", "", stripped)
            out.append(f"<li>{item}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        if stripped:
            out.append(f"<p>{stripped}</p>")
    if in_list:
        out.append("</ul>")
    return "".join(out)
