from app.eval.dataset import load_golden_set
from app.eval.runner import run_regression, summarize_run

CASES = load_golden_set()


def test_run_regression_scores_every_case_for_both_prompts():
    baseline_scores, candidate_scores = run_regression("crm_summary_v1", "crm_summary_v2", cases=CASES)
    assert len(baseline_scores) == len(CASES)
    assert len(candidate_scores) == len(CASES)
    assert {s.case_id for s in baseline_scores} == {c.id for c in CASES}


def test_baseline_schema_validity_is_high():
    baseline_scores, _ = run_regression("crm_summary_v1", "crm_summary_v2", cases=CASES)
    summary = summarize_run("crm_summary", "v1", baseline_scores)
    assert summary.schema_validity_pct == 100.0
    assert summary.total_cases == len(CASES)


def test_candidate_verbose_style_costs_more_than_baseline():
    baseline_scores, candidate_scores = run_regression("crm_summary_v1", "crm_summary_v2", cases=CASES)
    baseline_summary = summarize_run("crm_summary", "v1", baseline_scores)
    candidate_summary = summarize_run("crm_summary", "v2", candidate_scores)
    assert candidate_summary.avg_cost_usd >= baseline_summary.avg_cost_usd


def test_summarize_run_handles_empty_scores():
    summary = summarize_run("crm_summary", "v1", [])
    assert summary.total_cases == 0
    assert summary.schema_validity_pct == 0.0
