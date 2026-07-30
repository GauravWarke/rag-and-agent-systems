from app.eval.comparison import compare_runs
from app.eval.scoring import CaseScore


def _score(case_id, category, **overrides):
    base = {
        "case_id": case_id,
        "category": category,
        "schema_valid": True,
        "sentiment_correct": True,
        "urgency_correct": True,
        "field_correctness": 1.0,
        "summary_relevance": 1.0,
        "next_action_useful": True,
        "safety_issue": False,
        "latency_ms": 1.0,
        "cost_usd": 0.0001,
    }
    base.update(overrides)
    return CaseScore(**base)


def test_compare_runs_detects_newly_failing_case():
    baseline = [_score("a", "cat1"), _score("b", "cat1")]
    candidate = [_score("a", "cat1"), _score("b", "cat1", schema_valid=False, error="bad")]
    report = compare_runs(baseline, candidate)
    assert report.newly_failing == ["b"]
    assert report.newly_passing == []


def test_compare_runs_detects_newly_passing_case():
    baseline = [_score("a", "cat1", urgency_correct=False)]
    candidate = [_score("a", "cat1")]
    report = compare_runs(baseline, candidate)
    assert report.newly_passing == ["a"]


def test_compare_runs_detects_regressed_category():
    baseline = [_score("a", "billing"), _score("b", "billing")]
    candidate = [_score("a", "billing"), _score("b", "billing", sentiment_correct=False)]
    report = compare_runs(baseline, candidate)
    assert "billing" in report.regressed_categories


def test_compare_runs_computes_cost_and_latency_deltas():
    baseline = [_score("a", "cat1", cost_usd=0.001, latency_ms=10.0)]
    candidate = [_score("a", "cat1", cost_usd=0.0012, latency_ms=15.0)]
    report = compare_runs(baseline, candidate)
    assert report.cost_delta_pct == 20.0
    assert report.latency_delta_pct == 50.0


def test_compare_runs_detects_safety_regression():
    baseline = [_score("a", "cat1", safety_issue=False)]
    candidate = [_score("a", "cat1", safety_issue=True)]
    report = compare_runs(baseline, candidate)
    assert report.safety_failure_delta == 1
