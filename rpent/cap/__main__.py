"""CLI: python -m rpent.cap --suite libero_object_swap --task 3 --debug-seed 51

The ASPIRE-style loop for one cell: write a program, run an episode under
--planner program, debug from the recorded evidence, freeze on success.
Evaluate the frozen program on held-out seeds with plain rpent runs:

    python -m rpent.cli.main --env libero --suite S --task T --seed 1 \
        --planner program --program-file programs/S/tT/solve.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(prog="python -m rpent.cap", description=__doc__)
    ap.add_argument("--suite", required=True)
    ap.add_argument("--task", type=int, required=True)
    ap.add_argument("--debug-seed", type=int, default=51,
                    help="the seed the loop learns on; held-out evaluation "
                         "uses OTHER seeds with the frozen program")
    ap.add_argument("--model", default="deepseek-v4-flash")
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--max-attempts", type=int, default=6)
    ap.add_argument("--logs-root", default="logs")
    ap.add_argument("--extra-cli", nargs=argparse.REMAINDER, default=[],
                    help="passed through to rpent.cli.main (endpoints etc.)")
    args = ap.parse_args()

    from rpent.cap.loop import cap_loop

    result = cap_loop(
        suite=args.suite, task=args.task, debug_seed=args.debug_seed,
        model=args.model, base_url=args.base_url,
        max_attempts=args.max_attempts, logs_root=Path(args.logs_root),
        extra_cli=list(args.extra_cli),
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("solved") else 1


if __name__ == "__main__":
    sys.exit(main())
