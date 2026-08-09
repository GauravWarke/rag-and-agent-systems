from app.logs.synthetic import generate_synthetic_logs
from app.sampling.candidates import identify_candidates


def test_returns_top_n_sorted_descending():
    logs = generate_synthetic_logs(n=300, seed=1)
    candidates = identify_candidates(logs, top_n=15, seed=1)
    assert len(candidates) == 15
    scores = [c.score for c in candidates]
    assert scores == sorted(scores, reverse=True)


def test_failure_signals_score_higher_than_baseline():
    logs = generate_synthetic_logs(n=500, seed=1)
    candidates = identify_candidates(logs, top_n=len(logs), seed=1)
    by_id = {c.log_id: c for c in candidates}
    log_by_id = {log.id: log for log in logs}

    safety_scores = [by_id[lid].score for lid, log in log_by_id.items() if log.safety_flag]
    clean_scores = [
        by_id[lid].score
        for lid, log in log_by_id.items()
        if not log.safety_flag and not log.error and not log.malformed_output and log.user_feedback != "negative"
    ]
    assert safety_scores and clean_scores
    assert sum(safety_scores) / len(safety_scores) > sum(clean_scores) / len(clean_scores)


def test_high_impact_feature_adds_reason():
    logs = generate_synthetic_logs(n=100, seed=1)
    candidates = identify_candidates(logs, high_impact_features={"ticket_triage"}, top_n=len(logs), seed=1)
    log_by_id = {log.id: log for log in logs}
    for candidate in candidates:
        if log_by_id[candidate.log_id].feature == "ticket_triage":
            assert any("high-impact" in reason for reason in candidate.reasons)


def test_empty_logs_returns_empty():
    assert identify_candidates([]) == []
