"""Eval CLI (Phase 5, step 4).

Usage:
    python eval.py --strategy hybrid
    python eval.py --strategy dense --out reports/

Runs the golden Q&A set through the retrieval + generation pipeline for
`--strategy`, writes a Markdown scorecard for that strategy, and writes an
HTML dashboard comparing it against the dense-only baseline (skipped if
`--strategy` already is `dense`) so a reviewer can open one file and toggle
between strategies. This is the artifact a reviewer opens first.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from app.eval.report import render_html_dashboard, render_markdown
from app.eval.runner import run_eval

_DEFAULT_OUT = Path("reports")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eval.py",
        description="Run the golden Q&A eval suite against the retrieval + generation pipeline.",
    )
    parser.add_argument("--strategy", choices=["hybrid", "dense", "sparse"], default="hybrid",
                        help="Retrieval strategy to score (default: hybrid).")
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT,
                        help=f"Output directory for reports (default: {_DEFAULT_OUT}).")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    primary = run_eval(args.strategy)
    md_path = args.out / f"eval_{args.strategy}.md"
    md_path.write_text(render_markdown(primary), encoding="utf-8")

    summaries = {args.strategy: primary}
    if args.strategy != "dense":
        summaries["dense"] = run_eval("dense")

    dashboard_path = args.out / "dashboard.html"
    dashboard_path.write_text(render_html_dashboard(summaries), encoding="utf-8")

    print(f"Wrote {md_path} ({primary.total_cases} cases, "
          f"answer_correct_rate={primary.answer_correct_rate:.0%})")
    print(f"Wrote {dashboard_path} (strategies: {', '.join(summaries)})")
    return 0
