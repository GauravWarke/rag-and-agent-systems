from app.eval.comparison import ComparisonReport
from app.eval.runner import RunSummary
from app.eval.thresholds import GateDecision, evaluate_gate


def _summary(**overrides):
    base = {
        "prompt_name": "crm_summary",
        "prompt_version": "v1",
        "total_cases": 10,
        "schema_validity_pct": 100.0,
        "sentiment_accuracy_pct": 90.0,
        "urgency_accuracy_pct": 90.0,
        "next_action_useful_pct": 90.0,
        "avg_summary_relevance": 0.9,
        "safety_failure_count": 0,
        "avg_latency_ms": 1.0,
        "avg_cost_usd": 0.0001,
        "total_cost_usd": 0.001,
    }
    base.update(overrides)
    return RunSummary(**base)


def _report(baseline, candidate, **overrides):
    base = {
        "baseline": baseline,
        "candidate": candidate,
        "newly_failing": [],
        "newly_passing": [],
        "regressed_categories": [],
        "improved_categories": [],
        "schema_validity_delta_pct": 0.0,
        "cost_delta_pct": 0.0,
        "latency_delta_pct": 0.0,
        "safety_failure_delta": 0,
    }
    base.update(overrides)
    return ComparisonReport(**base)


def test_gate_passes_when_nothing_regressed():
    baseline = _summary()
    candidate = _summary()
    report = _report(baseline, candidate)
    result = evaluate_gate(report)
    assert result.decision == GateDecision.pass_


def test_gate_blocks_on_schema_validity_drop():
    baseline = _summary(schema_validity_pct=100.0)
    candidate = _summary(schema_validity_pct=95.0)
    report = _report(baseline, candidate)
    result = evaluate_gate(report, schema_validity_drop_block_pct=2.0)
    assert result.decision == GateDecision.block
    assert any("schema validity" in r for r in result.reasons)


def test_gate_blocks_on_safety_regression():
    baseline = _summary(safety_failure_count=0)
    candidate = _summary(safety_failure_count=2)
    report = _report(baseline, candidate, safety_failure_delta=2)
    result = evaluate_gate(report)
    assert result.decision == GateDecision.block
    assert any("safety" in r for r in result.reasons)


def test_gate_blocks_on_cost_increase():
    baseline = _summary(avg_cost_usd=0.001)
    candidate = _summary(avg_cost_usd=0.0015)
    report = _report(baseline, candidate, cost_delta_pct=50.0)
    result = evaluate_gate(report, cost_increase_block_pct=20.0)
    assert result.decision == GateDecision.block
    assert any("cost" in r for r in result.reasons)


def test_gate_warns_on_latency_increase_only():
    baseline = _summary()
    candidate = _summary()
    report = _report(baseline, candidate, latency_delta_pct=30.0)
    result = evaluate_gate(report, latency_increase_warn_pct=20.0)
    assert result.decision == GateDecision.warn


def test_gate_warns_on_regressed_category():
    baseline = _summary()
    candidate = _summary()
    report = _report(baseline, candidate, regressed_categories=["billing"])
    result = evaluate_gate(report)
    assert result.decision == GateDecision.warn
