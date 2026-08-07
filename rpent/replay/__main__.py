"""CLI: python -m rpent.replay <run_dir> [--out FILE]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rpent.replay.html import write_replay
from rpent.replay.loader import load_run


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Rebuild a run's evidence timeline from its artifacts.",
    )
    ap.add_argument("run_dir", help="a finished run's output directory")
    ap.add_argument("--out", default=None,
                    help="output HTML (default <run_dir>/replay.html)")
    ap.add_argument("--no-3d", action="store_true",
                    help="skip replay_3d.html (the point-cloud view)")
    args = ap.parse_args()

    run = load_run(args.run_dir)
    # 3D first, so the 2D header sees replay_3d.html and links to it.
    if not args.no_3d:
        from rpent.replay.three_d import write_3d_replay

        out3d = write_3d_replay(run)
        if out3d is not None:
            print(f"wrote {out3d}")
        else:
            print("no world maps stored — skipped the 3D view", file=sys.stderr)
    out = write_replay(run, Path(args.out) if args.out else None)
    print(f"wrote {out} — {len(run.calls)} calls, "
          f"{max((c.turn for c in run.calls), default=0)} turns"
          + (f", {len(run.warnings)} record gaps" if run.warnings else ""))
    for w in run.warnings:
        print(f"  gap: {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
