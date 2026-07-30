"""Regression runner (Phase 3, step 1): runs every golden case through
both the baseline (production) prompt and the candidate (changed) prompt,
scoring each independently so they can be compared run-over-run.
"""
from __future__ import annotations

from pydantic import BaseModel

from app.eval.dataset import GoldenCase, load_golden_set
from app.eval.scoring import CaseScore, score_case
from app.generation.summarizer import run_prompt
from app.prompts.loader import load_prompt


class RunSummary(BaseModel):
    prompt_name: str
    prompt_version: str
    total_cases: int
    schema_validity_pct: float
    sentiment_accuracy_pct: float
    urgency_accuracy_pct: float
    next_action_useful_pct: float
    avg_summary_relevance: float
    safety_failure_count: int
    avg_latency_ms: float
    avg_cost_usd: float
    total_cost_usd: float


def summarize_run(prompt_name: str, prompt_version: str, scores: list[CaseScore]) -> RunSummary:
    n = len(scores)
    if n == 0:
        return RunSummary(
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            total_cases=0,
            schema_validity_pct=0.0,
            sentiment_accuracy_pct=0.0,
            urgency_accuracy_pct=0.0,
            next_action_useful_pct=0.0,
            avg_summary_relevance=0.0,
            safety_failure_count=0,
            avg_latency_ms=0.0,
            avg_cost_usd=0.0,
            total_cost_usd=0.0,
        )
    return RunSummary(
        prompt_name=prompt_name,
        prompt_version=prompt_version,
        total_cases=n,
        schema_validity_pct=round(100 * sum(s.schema_valid for s in scores) / n, 2),
        sentiment_accuracy_pct=round(100 * sum(s.sentiment_correct for s in scores) / n, 2),
        urgency_accuracy_pct=round(100 * sum(s.urgency_correct for s in scores) / n, 2),
        next_action_useful_pct=round(100 * sum(s.next_action_useful for s in scores) / n, 2),
        avg_summary_relevance=round(sum(s.summary_relevance for s in scores) / n, 4),
        safety_failure_count=sum(s.safety_issue for s in scores),
        avg_latency_ms=round(sum(s.latency_ms for s in scores) / n, 4),
        avg_cost_usd=round(sum(s.cost_usd for s in scores) / n, 8),
        total_cost_usd=round(sum(s.cost_usd for s in scores), 8),
    )


def _run_one(cases: list[GoldenCase], prompt_name: str) -> list[CaseScore]:
    prompt = load_prompt(prompt_name)
    results = []
    for case in cases:
        raw, meta = run_prompt(case.note, prompt)
        results.append(score_case(case, raw, meta))
    return results


def run_regression(
    baseline_prompt: str,
    candidate_prompt: str,
    cases: list[GoldenCase] | None = None,
) -> tuple[list[CaseScore], list[CaseScore]]:
    """Run every golden case through both prompts. Returns
    (baseline_scores, candidate_scores), one `CaseScore` per case per run.
    """
    cases = load_golden_set() if cases is None else cases
    baseline_scores = _run_one(cases, baseline_prompt)
    candidate_scores = _run_one(cases, candidate_prompt)
    return baseline_scores, candidate_scores
