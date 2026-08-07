"""Emit the timeline as one self-contained HTML file beside the artifacts.

No server, no CDN, no build step: images are referenced by relative path,
markers are inline SVG scaled with the image, styling is a small embedded
stylesheet. The file is itself a reviewable artifact — the promotion gate's
reports deep-link into it via the ``#seq-N`` anchors.
"""
from __future__ import annotations

import html as html_escape
from pathlib import Path

from rpent.replay.loader import RunReplay
from rpent.replay.markdown import render_markdown
from rpent.replay.render import Card, Marker, Panel, render_call

_CSS = """
body { margin: 0; font: 14px/1.45 system-ui, sans-serif; background: #f6f7f9; color: #1c2330; }
header { background: #1c2330; color: #eef1f6; padding: 14px 22px; }
header .meta { font-size: 12px; color: #9fb0c9; margin-top: 4px; }
.ok { color: #35c26a; font-weight: 600; } .bad { color: #ff7a6e; font-weight: 600; }
main { max-width: 1080px; margin: 0 auto; padding: 18px; }
.turn { margin: 26px 0 10px; }
.reason { border-left: 3px solid #7a8cff; background: #eef0ff; padding: 8px 12px;
          border-radius: 0 6px 6px 0; color: #2c3550; }
.reason p { margin: 3px 0; } .reason ul { margin: 3px 0; padding-left: 18px; }
.reason code { background: #dde2f2; border-radius: 3px; padding: 0 3px; font-size: 12px; }
.card { background: #fff; border: 1px solid #dde3ec; border-radius: 8px;
        margin: 10px 0; padding: 10px 14px; }
.card:target { border-color: #7a8cff; box-shadow: 0 0 0 3px #7a8cff44; }
.card h3 { margin: 0 0 6px; font-size: 14px; }
.card h3 .seq { color: #8a94a6; font-weight: 400; font-size: 12px; }
.card h3 .adv { background: #ffe6c9; color: #8a5200; font-size: 11px;
                border-radius: 4px; padding: 1px 6px; margin-left: 8px; }
.card ul { margin: 4px 0; padding-left: 18px; }
.card li { margin: 2px 0; }
.panels { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 8px; }
.imgwrap { position: relative; width: 320px; }
.imgwrap img { width: 100%; display: block; border-radius: 4px; image-rendering: pixelated; }
.imgwrap svg { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
.imgwrap .cap { font-size: 11px; color: #67718a; margin-top: 2px; }
details { margin-top: 6px; } details summary { cursor: pointer; font-size: 12px; color: #67718a; }
details pre { background: #f0f2f7; padding: 8px; border-radius: 6px; overflow-x: auto;
              font-size: 11px; max-height: 400px; }
.warn { background: #fff4e5; border: 1px solid #ffd9a0; border-radius: 6px;
        padding: 8px 12px; font-size: 12px; margin: 12px 0; }
.err-line { color: #b3261e; }
"""

_MARK = {
    "point": '<circle cx="{x}" cy="{y}" r="{r}" fill="none" stroke="#35c26a" stroke-width="{w}"/>'
             '<circle cx="{x}" cy="{y}" r="1.2" fill="#35c26a"/>',
    "target": '<path d="M {x0} {y0} L {x1} {y1} M {x0} {y1} L {x1} {y0}" '
              'stroke="#ff3b30" stroke-width="{w}" fill="none"/>',
}


def _esc(text: object) -> str:
    return html_escape.escape(str(text), quote=True)


def _svg_markers(panel: Panel) -> str:
    parts = []
    r = max(panel.width, panel.height) * 0.02
    w = max(1.0, r * 0.35)
    for m in panel.markers:
        x, y = m.col, m.row
        if m.kind == "box" and m.row2 is not None:
            parts.append(
                f'<rect x="{min(m.col, m.col2)}" y="{min(m.row, m.row2)}" '
                f'width="{abs(m.col2 - m.col)}" height="{abs(m.row2 - m.row)}" '
                f'fill="none" stroke="#7a8cff" stroke-width="{w}"/>'
            )
        elif m.kind == "target":
            parts.append(_MARK["target"].format(x0=x - r, x1=x + r, y0=y - r, y1=y + r, w=w))
        else:
            parts.append(_MARK["point"].format(x=x, y=y, r=r, w=w))
        parts.append(
            f'<text x="{x + r + 2}" y="{y}" font-size="{max(8, r)}px" fill="#ffffff" '
            f'stroke="#000000" stroke-width="0.4" paint-order="stroke">{_esc(m.label)}</text>'
        )
    return "".join(parts)


def _panel_html(panel: Panel) -> str:
    svg = ""
    if panel.markers:
        svg = (f'<svg viewBox="0 0 {panel.width} {panel.height}" '
               f'preserveAspectRatio="none">{_svg_markers(panel)}</svg>')
    return (f'<div class="imgwrap"><img src="{_esc(panel.src)}" loading="lazy">'
            f'{svg}<div class="cap">{_esc(panel.caption)}</div></div>')


def _card_html(seq: int, advanced: bool, elapsed, card: Card) -> str:
    adv = '<span class="adv">env step</span>' if advanced else ""
    took = f" · {elapsed:.1f}s" if isinstance(elapsed, (int, float)) and elapsed >= 0.1 else ""
    lines = "".join(
        f'<li class="{"err-line" if line.startswith("ERROR") else ""}">{_esc(line)}</li>'
        for line in card.lines
    )
    panels = ""
    if card.panels:
        panels = f'<div class="panels">{"".join(_panel_html(p) for p in card.panels)}</div>'
    raw = ""
    if card.raw:
        raw = f"<details><summary>full result</summary><pre>{_esc(card.raw)}</pre></details>"
    return (
        f'<section class="card" id="seq-{seq}">'
        f'<h3><span class="seq">#{seq}{took}</span> {_esc(card.title)}{adv}</h3>'
        f"<ul>{lines}</ul>{panels}{raw}</section>"
    )


def render_html(run: RunReplay) -> str:
    status = ('<span class="ok">TERMINATED (success)</span>' if run.terminated
              else '<span class="bad">NOT TERMINATED</span>')
    finish = run.finish or {}
    profile = (run.sandbox or {}).get("profile", "—")
    header = (
        f"<header><b>{_esc(run.run_dir.name)}</b><br>"
        f"{_esc(run.task_language or '(task unknown)')} &nbsp; {status}"
        f'<div class="meta">model {_esc(run.model or "?")} · sandbox {_esc(profile)}'
        f' · {len(run.calls)} tool calls'
        + (f" · finish: {_esc(finish.get('status'))} — {_esc(finish.get('summary'))}"
           if finish else "")
        + (' · <a style="color:#9fb0c9" href="replay_3d.html">3D replay</a>'
           if (run.run_dir / "replay_3d.html").exists() else "")
        + "</div></header>"
    )

    warnings = ""
    if run.warnings:
        items = "".join(f"<li>{_esc(w)}</li>" for w in run.warnings)
        warnings = f'<div class="warn"><b>record gaps</b><ul>{items}</ul></div>'

    by_seq = {c.seq: c for c in run.calls}
    body: list[str] = []
    for turn in run.turns:
        body.append(f'<div class="turn"><b>turn {turn.index}</b></div>')
        # Segments preserve the message's own order: prose renders where it
        # was written, including between two calls and after the last one.
        for kind, value in turn.segments:
            if kind == "text":
                body.append(f'<div class="reason">{render_markdown(str(value))}</div>')
                continue
            call = by_seq.get(value)
            if call is None:
                continue
            card = render_call(call, run)
            body.append(_card_html(call.seq, call.advanced, call.elapsed_s, card))

    return (
        "<!doctype html><meta charset='utf-8'>"
        f"<title>replay {_esc(run.run_dir.name)}</title>"
        f"<style>{_CSS}</style>"
        f"{header}<main>{warnings}{''.join(body)}</main>"
    )


def write_replay(run: RunReplay, out: Path | None = None) -> Path:
    out = out or (run.run_dir / "replay.html")
    out.write_text(render_html(run))
    return out
