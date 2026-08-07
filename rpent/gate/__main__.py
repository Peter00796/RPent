"""CLI: python -m rpent.gate {observe,synthesize,review,apply,ledger} ...

    observe    RUN_DIR...        per-run, library-blind observations (LLM)
    synthesize RUN_DIR...        sweep-wide proposals + HARNESS_REVIEW.md (LLM)
    review     RUN_DIR...        five checks -> report.html + verdicts.yaml
    apply      VERDICTS.yaml     execute the human-edited verdicts
    ledger     RUN_DIR...        consumption track record per library entry

A sweep is whatever run set you pass — 5, 10, 20 repeats of a task, or a
hand-picked set of failures.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rpent.utils.config import get_repo_root


def _default_memory_root() -> Path:
    return get_repo_root() / "memory"


def _cmd_review(args) -> int:
    from rpent.gate import tokens
    from rpent.gate.checks import run_checks
    from rpent.gate.proposal import collect_proposals
    from rpent.gate.report import write_report

    run_dirs = [Path(d) for d in args.runs]
    runs = tokens.run_map(run_dirs)
    proposals = collect_proposals(run_dirs,
                                  [Path(d) for d in (args.proposals or [])])
    if not proposals:
        print("no proposals under the given runs' memory_proposals/ dirs",
              file=sys.stderr)
        return 1
    memory_root = Path(args.memory_root)
    reviews = [run_checks(p, runs, memory_root, args.env, proposals)
               for p in proposals]
    out_dir = Path(args.out) if args.out else (run_dirs[0].parent / "gate_review")
    report, verdicts = write_report(reviews, out_dir, runs)
    counts = {v: sum(1 for r in reviews if r.suggested == v)
              for v in ("admit", "hold", "reject")}
    print(f"{len(reviews)} proposals — suggested {counts['admit']} admit, "
          f"{counts['hold']} hold, {counts['reject']} reject")
    print(f"report:   {report}")
    print(f"verdicts: {verdicts}   <- edit this, then: "
          f"python -m rpent.gate apply {verdicts}")
    return 0


def _cmd_apply(args) -> int:
    from rpent.gate.apply import apply_verdicts

    summary = apply_verdicts(args.verdicts, args.memory_root)
    print(summary)
    print("\ncommit the library to seal the generation, e.g.:\n"
          '  git add memory && git commit -m "memory: <generation note>"')
    return 0


def _cmd_ledger(args) -> int:
    from rpent.gate.ledger import scan, write_ledger

    result = scan([Path(d) for d in args.runs], Path(args.memory_root))
    out = write_ledger(result, Path(args.memory_root))
    print(f"scanned {result['runs_scanned']} runs -> {out}")
    for rel, slot in sorted(result["entries"].items()):
        print(f"  {rel}: {slot['reads']} reads in {slot['consulted_runs']} runs "
              f"({slot['successes']} success / {slot['failures']} fail)")
    for line in result["recommendations"]:
        print(f"  ! {line}")
    return 0


def _cmd_observe(args) -> int:
    from rpent.gate.observe import observe_run

    for run_dir in args.runs:
        written = observe_run(Path(run_dir), args.model, args.base_url)
        print(f"{run_dir}: {len(written)} observations")
    return 0


def _cmd_synthesize(args) -> int:
    from rpent.gate.synthesize import synthesize

    run_dirs = [Path(d) for d in args.runs]
    out_dir = Path(args.out) if args.out else (run_dirs[0].parent / "gate_review")
    result = synthesize(run_dirs, Path(args.memory_root), out_dir,
                        args.model, args.base_url)
    print(f"{len(result['proposals'])} proposals -> {out_dir / 'proposals'}")
    print(f"memo -> {result['memo']}")
    print("next: python -m rpent.gate review "
          + " ".join(str(d) for d in run_dirs)
          + f" --proposals {out_dir / 'proposals'} --out {out_dir}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="python -m rpent.gate",
                                 description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    observe = sub.add_parser("observe", help="per-run library-blind observations (LLM)")
    observe.add_argument("runs", nargs="+")
    observe.add_argument("--model", default="deepseek-v4-flash")
    observe.add_argument("--base-url", default=None)
    observe.set_defaults(fn=_cmd_observe)

    synth = sub.add_parser("synthesize",
                           help="sweep-wide proposals + harness memo (LLM)")
    synth.add_argument("runs", nargs="+")
    synth.add_argument("--model", default="deepseek-v4-flash")
    synth.add_argument("--base-url", default=None)
    synth.add_argument("--memory-root", default=str(_default_memory_root()))
    synth.add_argument("--out", default=None)
    synth.set_defaults(fn=_cmd_synthesize)

    review = sub.add_parser("review", help="check proposals, write report + verdicts")
    review.add_argument("runs", nargs="+", help="run output dirs (any number — "
                        "a sweep of 5, 10, 20 …)")
    review.add_argument("--proposals", nargs="*", default=None,
                        help="extra dirs of proposal .md files "
                             "(e.g. the synthesizer's output)")
    review.add_argument("--memory-root", default=str(_default_memory_root()))
    review.add_argument("--env", default="libero")
    review.add_argument("--out", default=None,
                        help="review dir (default <runs parent>/gate_review)")
    review.set_defaults(fn=_cmd_review)

    apply_ = sub.add_parser("apply", help="execute the edited verdicts.yaml")
    apply_.add_argument("verdicts")
    apply_.add_argument("--memory-root", default=str(_default_memory_root()))
    apply_.set_defaults(fn=_cmd_apply)

    ledger = sub.add_parser("ledger", help="consumption track record per entry")
    ledger.add_argument("runs", nargs="+")
    ledger.add_argument("--memory-root", default=str(_default_memory_root()))
    ledger.set_defaults(fn=_cmd_ledger)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
