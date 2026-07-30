from app.eval.comparison import case_passes, compare_runs
from app.eval.dataset import load_golden_set
from app.eval.report import build_case_diffs, render_pr_comment, render_release_report
from app.eval.runner import run_regression_detailed
from app.eval.thresholds import GateDecision, evaluate_gate

CASES = load_golden_set()


def test_build_case_diffs_only_includes_failed_candidate_cases():
    cases, baseline_results, candidate_results = run_regression_detailed(
        "crm_summary_v1", "crm_summary_v2", cases=CASES
    )
    diffs = build_case_diffs(cases, baseline_results, candidate_results)
    candidate_by_id = {r.case_id: r for r in candidate_results}
    for diff in diffs:
        assert not case_passes(candidate_by_id[diff.case_id].score)


def test_build_case_diffs_includes_input_and_both_outputs():
    cases, baseline_results, candidate_results = run_regression_detailed(
        "crm_summary_v1", "crm_summary_v2", cases=CASES
    )
    diffs = build_case_diffs(cases, baseline_results, candidate_results)
    if diffs:
        diff = diffs[0]
        assert diff.note
        assert isinstance(diff.baseline_output, dict)
        assert isinstance(diff.candidate_output, dict)
        assert diff.explanation


def test_render_release_report_contains_scorecard_and_decision():
    baseline_scores, candidate_scores = _plain_scores()
    comparison = compare_runs(baseline_scores, candidate_scores)
    gate = evaluate_gate(comparison)
    report = render_release_report(comparison, gate, [])
    assert "# Prompt Release Report" in report
    assert "Scorecard" in report
    assert "PASS" in report


def test_render_pr_comment_includes_decision_and_link():
    baseline_scores, candidate_scores = _plain_scores()
    comparison = compare_runs(baseline_scores, candidate_scores)
    gate = evaluate_gate(comparison)
    comment = render_pr_comment(comparison, gate, report_artifact_url="https://example.test/report")
    assert "Prompt Release Gate" in comment
    assert "https://example.test/report" in comment


def test_render_pr_comment_without_link_omits_link_section():
    baseline_scores, candidate_scores = _plain_scores()
    comparison = compare_runs(baseline_scores, candidate_scores)
    gate = evaluate_gate(comparison)
    comment = render_pr_comment(comparison, gate)
    assert "Full report" not in comment


def _plain_scores():
    from app.eval.scoring import CaseScore

    baseline = [
        CaseScore(
            case_id="a",
            category="billing",
            schema_valid=True,
            sentiment_correct=True,
            urgency_correct=True,
            field_correctness=1.0,
            summary_relevance=1.0,
            next_action_useful=True,
            safety_issue=False,
            latency_ms=1.0,
            cost_usd=0.0001,
        )
    ]
    candidate = [
        CaseScore(
            case_id="a",
            category="billing",
            schema_valid=True,
            sentiment_correct=True,
            urgency_correct=True,
            field_correctness=1.0,
            summary_relevance=1.0,
            next_action_useful=True,
            safety_issue=False,
            latency_ms=1.0,
            cost_usd=0.0001,
        )
    ]
    return baseline, candidate


def test_gate_decision_type_is_enum():
    assert GateDecision.pass_ in GateDecision
