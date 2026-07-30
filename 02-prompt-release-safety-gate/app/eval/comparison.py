"""Compare a candidate run to the baseline run (Phase 3, step 3).

This diff — which cases newly fail, which categories regressed, how cost
and latency moved — is the core value of the regression runner.
"""
from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel

from app.eval.runner import RunSummary, summarize_run
from app.eval.scoring import CaseScore


def _case_passes(score: CaseScore) -> bool:
    return (
        score.schema_valid
        and score.sentiment_correct
        and score.urgency_correct
        and score.next_action_useful
        and not score.safety_issue
    )


class ComparisonReport(BaseModel):
    baseline: RunSummary
    candidate: RunSummary
    newly_failing: list[str]
    newly_passing: list[str]
    regressed_categories: list[str]
    improved_categories: list[str]
    schema_validity_delta_pct: float
    cost_delta_pct: float
    latency_delta_pct: float
    safety_failure_delta: int


def _pct_delta(baseline: float, candidate: float) -> float:
    if baseline == 0:
        return 0.0 if candidate == 0 else 100.0
    return round(100 * (candidate - baseline) / baseline, 2)


def compare_runs(baseline_scores: list[CaseScore], candidate_scores: list[CaseScore]) -> ComparisonReport:
    baseline_by_id = {s.case_id: s for s in baseline_scores}
    candidate_by_id = {s.case_id: s for s in candidate_scores}

    newly_failing = []
    newly_passing = []
    for case_id, baseline_score in baseline_by_id.items():
        candidate_score = candidate_by_id.get(case_id)
        if candidate_score is None:
            continue
        was_passing = _case_passes(baseline_score)
        now_passing = _case_passes(candidate_score)
        if was_passing and not now_passing:
            newly_failing.append(case_id)
        elif not was_passing and now_passing:
            newly_passing.append(case_id)

    baseline_by_category: dict[str, list[CaseScore]] = defaultdict(list)
    candidate_by_category: dict[str, list[CaseScore]] = defaultdict(list)
    for s in baseline_scores:
        baseline_by_category[s.category].append(s)
    for s in candidate_scores:
        candidate_by_category[s.category].append(s)

    regressed_categories = []
    improved_categories = []
    for category, baseline_group in baseline_by_category.items():
        candidate_group = candidate_by_category.get(category, [])
        if not candidate_group:
            continue
        baseline_pass_rate = sum(_case_passes(s) for s in baseline_group) / len(baseline_group)
        candidate_pass_rate = sum(_case_passes(s) for s in candidate_group) / len(candidate_group)
        if candidate_pass_rate < baseline_pass_rate:
            regressed_categories.append(category)
        elif candidate_pass_rate > baseline_pass_rate:
            improved_categories.append(category)

    baseline_summary = summarize_run("baseline", "baseline", baseline_scores)
    candidate_summary = summarize_run("candidate", "candidate", candidate_scores)

    return ComparisonReport(
        baseline=baseline_summary,
        candidate=candidate_summary,
        newly_failing=sorted(newly_failing),
        newly_passing=sorted(newly_passing),
        regressed_categories=sorted(regressed_categories),
        improved_categories=sorted(improved_categories),
        schema_validity_delta_pct=_pct_delta(
            baseline_summary.schema_validity_pct, candidate_summary.schema_validity_pct
        ),
        cost_delta_pct=_pct_delta(baseline_summary.avg_cost_usd, candidate_summary.avg_cost_usd),
        latency_delta_pct=_pct_delta(baseline_summary.avg_latency_ms, candidate_summary.avg_latency_ms),
        safety_failure_delta=candidate_summary.safety_failure_count - baseline_summary.safety_failure_count,
    )
