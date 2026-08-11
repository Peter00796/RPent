"""CLI: python -m rpent.practice --suite S --task N [--practice-seeds 51,52]

The ASPIRE-style debugger for the turn-loop arm: iterate one cell on
practice seeds, mining every failure into its task playbook through the
gate's mechanical checks, escalating to a targeted experiment when
knowledge stalls, and sitting the scoring-seed exam only when practice
passes. Report says how many exams were taken — that number is part of
any claim built on the result.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suite", required=True)
    ap.add_argument("--task", type=int, required=True)
    ap.add_argument("--practice-seeds", default="51,52",
                    help="comma list, learning happens here (default 51,52)")
    ap.add_argument("--exam-seed", type=int, default=0,
                    help="the scoring seed; one attempt per exam (default 0)")
    ap.add_argument("--max-rounds", type=int, default=5)
    ap.add_argument("--max-exams", type=int, default=2)
    ap.add_argument("--model", default="deepseek-v4-flash")
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--logs-root", default="logs")
    args = ap.parse_args()

    seeds = [int(s) for s in args.practice_seeds.split(",")]
    if any(s < 51 for s in seeds):
        ap.error("practice seeds must be >= 51 (scoring seeds are exams only)")
    if args.exam_seed in seeds:
        ap.error("the exam seed cannot be a practice seed")

    from rpent.practice.loop import practice_loop

    result = practice_loop(
        suite=args.suite, task=args.task, practice_seeds=seeds,
        exam_seed=args.exam_seed, max_rounds=args.max_rounds,
        max_exams=args.max_exams, model=args.model, base_url=args.base_url,
        logs_root=Path(args.logs_root))
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("solved") else 1


if __name__ == "__main__":
    sys.exit(main())
