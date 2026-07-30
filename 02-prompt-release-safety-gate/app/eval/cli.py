"""Release gate CLI (Phase 5, step 3): run the regression suite for the
configured baseline/candidate prompts, write the release report and PR
comment to disk, print the decision, and return a process exit code CI can
act on.

Usage:
    python gate.py
    python gate.py --baseline crm_summary_v1 --candidate crm_summary_v2 --out reports/
"""
from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import settings
from app.eval.comparison import compare_runs
from app.eval.report import build_case_diffs, render_pr_comment, render_release_report
from app.eval.runner import run_regression_detailed
from app.eval.thresholds import GateDecision, evaluate_gate

_DEFAULT_OUT = Path("reports")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gate.py",
        description="Run the prompt regression suite and render a release gate report.",
    )
    parser.add_argument("--baseline", default=settings.baseline_prompt,
                        help=f"Baseline prompt name (default: {settings.baseline_prompt}).")
    parser.add_argument("--candidate", default=settings.candidate_prompt,
                        help=f"Candidate prompt name (default: {settings.candidate_prompt}).")
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT,
                        help=f"Output directory for reports (default: {_DEFAULT_OUT}).")
    parser.add_argument("--report-url", default=None,
                        help="URL to the full report artifact, embedded in the PR comment.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    cases, baseline_results, candidate_results = run_regression_detailed(args.baseline, args.candidate)
    baseline_scores = [r.score for r in baseline_results]
    candidate_scores = [r.score for r in candidate_results]

    comparison = compare_runs(baseline_scores, candidate_scores)
    gate = evaluate_gate(comparison)
    diffs = build_case_diffs(cases, baseline_results, candidate_results)

    report_path = args.out / "release_report.md"
    report_path.write_text(render_release_report(comparison, gate, diffs), encoding="utf-8")

    comment_path = args.out / "pr_comment.md"
    comment_path.write_text(render_pr_comment(comparison, gate, args.report_url), encoding="utf-8")

    print(f"Wrote {report_path} and {comment_path}")
    print(f"Gate decision: {gate.decision.value}")
    for reason in gate.reasons:
        print(f"  - {reason}")

    return 1 if gate.decision == GateDecision.block else 0
