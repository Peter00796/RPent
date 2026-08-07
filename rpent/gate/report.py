"""The gate's output surface: report.html for eyes, verdicts.yaml for hands.

The report renders one card per proposal — contract fields, the five checks'
findings, and every citation resolved to what the record actually says, deep
linked into that run's ``replay.html``. The verdicts file is the interrupt:
the gate prefills its suggestion, the human edits ``verdict:`` lines, and
``gate apply`` executes exactly what the file says. Rejections keep their
reasons — negative results are part of the record.
"""
from __future__ import annotations

import html as html_escape
import os
from pathlib import Path

from rpent.gate.checks import Review

_CSS = """
body { margin:0; font:14px/1.5 system-ui,sans-serif; background:#f6f7f9; color:#1c2330; }
header { background:#1c2330; color:#eef1f6; padding:14px 22px; }
header .meta { font-size:12px; color:#9fb0c9; margin-top:4px; }
main { max-width: 1000px; margin: 0 auto; padding: 18px; }
.card { background:#fff; border:1px solid #dde3ec; border-radius:8px; margin:14px 0;
        padding:12px 16px; border-left:5px solid #b9c4de; }
.card.admit { border-left-color:#35c26a; } .card.hold { border-left-color:#f0a03c; }
.card.reject { border-left-color:#ff5a4e; }
.card h3 { margin:0 0 2px; font-size:15px; }
.badge { font-size:11px; border-radius:4px; padding:1px 7px; margin-left:8px;
         background:#eef0f5; color:#4a5468; }
.suggest { float:right; font-weight:700; font-size:12px; text-transform:uppercase; }
.suggest.admit { color:#1d8a4a; } .suggest.hold { color:#b06a10; } .suggest.reject { color:#c2352b; }
.fields { font-size:12px; color:#67718a; margin:2px 0 8px; }
.findings li { font-size:13px; margin:2px 0; }
.findings .reject { color:#c2352b; } .findings .flag { color:#b06a10; }
.findings .ok { color:#5f6b80; }
.cites { margin-top:8px; border-top:1px dashed #dde3ec; padding-top:6px; }
.cite { font-size:12px; margin:3px 0; color:#3c4557; }
.cite code { background:#f0f2f7; border-radius:3px; padding:0 4px; font-size:11px; }
.cite.missing { color:#c2352b; }
.body { background:#f8f9fc; border-radius:6px; padding:8px 12px; font-size:13px;
        margin-top:8px; white-space:pre-wrap; }
"""


def _esc(x: object) -> str:
    return html_escape.escape(str(x), quote=True)


def _card(review: Review, out_dir: Path, runs: dict[str, Path]) -> str:
    p = review.proposal
    suggested = review.suggested
    findings = "".join(
        f'<li class="{f.level}">[{f.check}] {_esc(f.message)}</li>'
        for f in review.findings
    ) or '<li class="ok">all checks passed</li>'
    cites = []
    for r in review.resolutions:
        if r.exists and r.replay_href and r.cite.run in runs:
            rel = os.path.relpath(runs[r.cite.run], out_dir)
            link = f' <a href="{_esc(rel)}/{_esc(r.replay_href)}">replay ↗</a>'
        else:
            link = ""
        cls = "cite" if r.exists else "cite missing"
        cites.append(f'<div class="{cls}"><code>{_esc(r.cite.raw)}</code> '
                     f"{_esc(r.summary)}{link}</div>")
    return (
        f'<section class="card {suggested}">'
        f'<span class="suggest {suggested}">{suggested}</span>'
        f"<h3>{_esc(p.title or p.path.name)}"
        f'<span class="badge">{_esc(p.action)}</span>'
        f'<span class="badge">{_esc(p.type)}</span>'
        f'<span class="badge">scope: {_esc(p.scope)}</span></h3>'
        f'<div class="fields">{_esc(p.path)}'
        + (f" → {_esc(review.destination)}" if review.destination else "")
        + (f"<br>conditions: {_esc(p.conditions)}" if p.conditions else "")
        + "</div>"
        f'<ul class="findings">{findings}</ul>'
        f'<div class="cites">{"".join(cites)}</div>'
        f'<details><summary style="font-size:12px;color:#67718a">body</summary>'
        f'<div class="body">{_esc(p.body)}</div></details>'
        "</section>"
    )


def write_report(reviews: list[Review], out_dir: Path,
                 runs: dict[str, Path]) -> tuple[Path, Path]:
    """Write report.html + verdicts.yaml; returns both paths."""
    import yaml

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    counts = {"admit": 0, "hold": 0, "reject": 0}
    for review in reviews:
        counts[review.suggested] += 1
    header = (
        "<header><b>Promotion gate review</b>"
        f'<div class="meta">{len(reviews)} proposals from {len(runs)} runs — '
        f"suggested: {counts['admit']} admit · {counts['hold']} hold · "
        f"{counts['reject']} reject. Edit verdicts.yaml, then run "
        "<code>python -m rpent.gate apply verdicts.yaml</code>.</div></header>"
    )
    cards = "".join(_card(r, out_dir, runs) for r in reviews)
    report_path = out_dir / "report.html"
    report_path.write_text(
        "<!doctype html><meta charset='utf-8'><title>gate review</title>"
        f"<style>{_CSS}</style>{header}<main>{cards}</main>"
    )

    verdicts = [
        {
            "proposal": str(r.proposal.path),
            "title": r.proposal.title,
            "action": r.proposal.action,
            "destination": r.destination,
            "suggested": r.suggested,
            # the human's line — prefilled with the suggestion:
            "verdict": r.suggested,
            "reasons": [f"[{f.check}] {f.message}" for f in r.findings
                        if f.level in ("reject", "flag")],
        }
        for r in reviews
    ]
    verdicts_path = out_dir / "verdicts.yaml"
    verdicts_path.write_text(yaml.safe_dump(verdicts, allow_unicode=True, sort_keys=False))
    return report_path, verdicts_path
