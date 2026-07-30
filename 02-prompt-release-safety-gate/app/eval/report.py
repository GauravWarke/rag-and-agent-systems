"""Release reports and PR comments (Phase 4): turn a `ComparisonReport` +
`GateResult` + per-case diffs into human-readable artifacts — a full
Markdown report for reviewers and a short PR-comment summary for CI.
"""
from __future__ import annotations

from pydantic import BaseModel

from app.eval.comparison import ComparisonReport, case_passes
from app.eval.dataset import GoldenCase
from app.eval.runner import DetailedCaseResult
from app.eval.thresholds import GateDecision, GateResult

_DECISION_EMOJI = {
    GateDecision.pass_: "✅ PASS",
    GateDecision.warn: "⚠️ WARN",
    GateDecision.block: "⛔ BLOCK",
}


class CaseDiff(BaseModel):
    case_id: str
    category: str
    note: str
    expected_sentiment: str
    expected_urgency: str
    expected_summary_keywords: list[str]
    expected_next_action_keywords: list[str]
    baseline_output: dict
    candidate_output: dict
    explanation: str


def _explain(score) -> str:
    if score.error:
        return f"error: {score.error}"
    reasons = []
    if not score.schema_valid:
        reasons.append("schema invalid")
    if not score.sentiment_correct:
        reasons.append("sentiment mismatch")
    if not score.urgency_correct:
        reasons.append("urgency mismatch")
    if not score.next_action_useful:
        reasons.append("next action not useful")
    if score.safety_issue:
        reasons.append(f"safety issue ({score.safety_evidence})")
    return "; ".join(reasons) if reasons else "passes all checks"


def build_case_diffs(
    cases: list[GoldenCase],
    baseline_results: list[DetailedCaseResult],
    candidate_results: list[DetailedCaseResult],
) -> list[CaseDiff]:
    """Build a side-by-side diff for every case that fails on the
    candidate prompt, so a reviewer can see input, both outputs, the
    expected output, and why the candidate failed.
    """
    baseline_by_id = {r.case_id: r for r in baseline_results}
    candidate_by_id = {r.case_id: r for r in candidate_results}

    diffs = []
    for case in cases:
        candidate_result = candidate_by_id.get(case.id)
        baseline_result = baseline_by_id.get(case.id)
        if candidate_result is None or baseline_result is None:
            continue
        if case_passes(candidate_result.score):
            continue
        diffs.append(
            CaseDiff(
                case_id=case.id,
                category=case.category,
                note=case.note,
                expected_sentiment=case.expected.sentiment,
                expected_urgency=case.expected.urgency,
                expected_summary_keywords=case.expected.summary_keywords,
                expected_next_action_keywords=case.expected.next_action_keywords,
                baseline_output=baseline_result.raw_output,
                candidate_output=candidate_result.raw_output,
                explanation=_explain(candidate_result.score),
            )
        )
    return sorted(diffs, key=lambda d: d.case_id)


def _scorecard_table(comparison: ComparisonReport) -> str:
    b, c = comparison.baseline, comparison.candidate
    rows = [
        ("Schema validity %", b.schema_validity_pct, c.schema_validity_pct),
        ("Sentiment accuracy %", b.sentiment_accuracy_pct, c.sentiment_accuracy_pct),
        ("Urgency accuracy %", b.urgency_accuracy_pct, c.urgency_accuracy_pct),
        ("Next-action useful %", b.next_action_useful_pct, c.next_action_useful_pct),
        ("Avg summary relevance", b.avg_summary_relevance, c.avg_summary_relevance),
        ("Safety failures", b.safety_failure_count, c.safety_failure_count),
        ("Avg latency (ms)", b.avg_latency_ms, c.avg_latency_ms),
        ("Avg cost (USD)", b.avg_cost_usd, c.avg_cost_usd),
        ("Total cost (USD)", b.total_cost_usd, c.total_cost_usd),
    ]
    lines = ["| Metric | Baseline | Candidate |", "|---|---|---|"]
    lines += [f"| {name} | {base} | {cand} |" for name, base, cand in rows]
    return "\n".join(lines)


def render_release_report(
    comparison: ComparisonReport,
    gate: GateResult,
    diffs: list[CaseDiff],
) -> str:
    """Render the full Markdown release report: scorecard, regression
    table, side-by-side diffs for every failed case, cost/latency delta,
    and the recommended release decision.
    """
    lines = [
        "# Prompt Release Report",
        "",
        f"**Recommendation: {_DECISION_EMOJI[gate.decision]}**",
        "",
        "## Reasons",
        "",
        *[f"- {reason}" for reason in gate.reasons],
        "",
        "## Scorecard",
        "",
        _scorecard_table(comparison),
        "",
        "## Deltas",
        "",
        f"- Schema validity: {comparison.schema_validity_delta_pct:+.2f} points",
        f"- Cost: {comparison.cost_delta_pct:+.2f}%",
        f"- Latency: {comparison.latency_delta_pct:+.2f}%",
        f"- Safety failures: {comparison.safety_failure_delta:+d}",
        "",
        "## Regressions",
        "",
        f"- Newly failing cases ({len(comparison.newly_failing)}): "
        + (", ".join(comparison.newly_failing) if comparison.newly_failing else "none"),
        f"- Newly passing cases ({len(comparison.newly_passing)}): "
        + (", ".join(comparison.newly_passing) if comparison.newly_passing else "none"),
        "- Regressed categories: "
        + (", ".join(comparison.regressed_categories) if comparison.regressed_categories else "none"),
        "- Improved categories: "
        + (", ".join(comparison.improved_categories) if comparison.improved_categories else "none"),
        "",
        f"## Failed Case Diffs ({len(diffs)})",
        "",
    ]
    if not diffs:
        lines.append("No failing cases on the candidate prompt.")
    for diff in diffs:
        lines += [
            f"### {diff.case_id} ({diff.category})",
            "",
            f"- **Input:** {diff.note}",
            (
                f"- **Expected:** sentiment={diff.expected_sentiment}, urgency={diff.expected_urgency}, "
                f"summary keywords={diff.expected_summary_keywords}, "
                f"next-action keywords={diff.expected_next_action_keywords}"
            ),
            f"- **Baseline output:** {diff.baseline_output}",
            f"- **Candidate output:** {diff.candidate_output}",
            f"- **Why it failed:** {diff.explanation}",
            "",
        ]
    return "\n".join(lines)


def render_pr_comment(
    comparison: ComparisonReport,
    gate: GateResult,
    report_artifact_url: str | None = None,
) -> str:
    """Render the short PR-comment summary the CI job posts: decision,
    top regressions, metric deltas, and a link to the full report.
    """
    top_regressions = comparison.newly_failing[:5]
    lines = [
        f"### Prompt Release Gate: {_DECISION_EMOJI[gate.decision]}",
        "",
        *[f"- {reason}" for reason in gate.reasons],
        "",
        (
            f"**Metric deltas** — schema validity {comparison.schema_validity_delta_pct:+.2f}pp, "
            f"cost {comparison.cost_delta_pct:+.2f}%, latency {comparison.latency_delta_pct:+.2f}%, "
            f"safety failures {comparison.safety_failure_delta:+d}"
        ),
        "",
    ]
    if top_regressions:
        lines.append(f"**Top regressions:** {', '.join(top_regressions)}")
    else:
        lines.append("**Top regressions:** none")
    if report_artifact_url:
        lines += ["", f"[Full report]({report_artifact_url})"]
    return "\n".join(lines)
