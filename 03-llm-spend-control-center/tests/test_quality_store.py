from datetime import datetime, timezone

from app.quality.store import QualityCheckEntry, QualityStore


def _entry(**overrides) -> QualityCheckEntry:
    base = {
        "request_id": "r1",
        "timestamp": datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc),
        "team_id": "team-alpha",
        "feature": "support-bot",
        "cheap_model": "stub-fast",
        "reference_model": "stub-strong",
        "similarity_score": 0.9,
        "is_routing_miss": False,
        "prompt_preview": "hello",
    }
    base.update(overrides)
    return QualityCheckEntry(**base)


def test_log_and_all():
    store = QualityStore()
    store.log(_entry())
    assert len(store.all()) == 1


def test_misses_filters_to_routing_misses_only():
    store = QualityStore()
    store.log(_entry(request_id="r1", is_routing_miss=False))
    store.log(_entry(request_id="r2", is_routing_miss=True))
    misses = store.misses()
    assert len(misses) == 1
    assert misses[0].request_id == "r2"


def test_miss_rate_for_feature_is_zero_with_no_samples():
    store = QualityStore()
    assert store.miss_rate_for_feature("unknown-feature") == 0.0


def test_miss_rate_for_feature_computes_ratio():
    store = QualityStore()
    store.log(_entry(request_id="r1", feature="a", is_routing_miss=True))
    store.log(_entry(request_id="r2", feature="a", is_routing_miss=False))
    store.log(_entry(request_id="r3", feature="b", is_routing_miss=True))
    assert store.miss_rate_for_feature("a") == 0.5
    assert store.miss_rate_for_feature("b") == 1.0


def test_should_escalate_requires_min_samples_and_miss_rate():
    store = QualityStore()
    store.log(_entry(request_id="r1", feature="flaky", is_routing_miss=True))
    # Only one sample so far -- not enough evidence yet.
    assert store.should_escalate("flaky", min_samples=2, miss_rate_threshold=0.5) is False
    store.log(_entry(request_id="r2", feature="flaky", is_routing_miss=True))
    assert store.should_escalate("flaky", min_samples=2, miss_rate_threshold=0.5) is True


def test_should_escalate_false_when_miss_rate_too_low():
    store = QualityStore()
    store.log(_entry(request_id="r1", feature="reliable", is_routing_miss=False))
    store.log(_entry(request_id="r2", feature="reliable", is_routing_miss=False))
    assert store.should_escalate("reliable", min_samples=2, miss_rate_threshold=0.5) is False


def test_pass_rate_defaults_to_one_with_no_entries():
    store = QualityStore()
    assert store.pass_rate() == 1.0


def test_pass_rate_computes_from_misses():
    store = QualityStore()
    store.log(_entry(request_id="r1", is_routing_miss=True))
    store.log(_entry(request_id="r2", is_routing_miss=False))
    store.log(_entry(request_id="r3", is_routing_miss=False))
    store.log(_entry(request_id="r4", is_routing_miss=False))
    assert store.pass_rate() == 0.75
