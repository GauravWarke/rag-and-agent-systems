from app.logs.synthetic import FEATURES, generate_synthetic_logs


def test_generates_requested_count():
    logs = generate_synthetic_logs(n=200, seed=1)
    assert len(logs) == 200


def _content(log):
    # id (uuid4) and timestamp (relative to wall-clock "now") vary run to
    # run by design; everything else should be fully determined by the seed.
    data = log.model_dump()
    data.pop("id")
    data.pop("timestamp")
    return data


def test_deterministic_given_seed():
    a = generate_synthetic_logs(n=50, seed=7)
    b = generate_synthetic_logs(n=50, seed=7)
    assert [_content(log) for log in a] == [_content(log) for log in b]


def test_different_seed_differs():
    a = generate_synthetic_logs(n=50, seed=1)
    b = generate_synthetic_logs(n=50, seed=2)
    assert [log.prompt for log in a] != [log.prompt for log in b]


def test_covers_all_features():
    logs = generate_synthetic_logs(n=500, seed=3)
    seen_features = {log.feature for log in logs}
    assert seen_features == set(FEATURES)


def test_includes_quality_edge_cases():
    logs = generate_synthetic_logs(n=1000, seed=42)
    assert any(log.error for log in logs)
    assert any(log.malformed_output for log in logs)
    assert any(log.safety_flag for log in logs)
    assert any(log.retry_count > 0 for log in logs)
    assert any(log.user_feedback == "negative" for log in logs)
    assert any(log.user_feedback == "positive" for log in logs)


def test_seeded_pii_gets_redacted():
    logs = generate_synthetic_logs(n=1000, seed=42)
    assert any(log.redacted for log in logs)
    for log in logs:
        assert "@example.com" not in log.prompt
