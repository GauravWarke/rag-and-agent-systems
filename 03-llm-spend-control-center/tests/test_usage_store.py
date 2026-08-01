from datetime import datetime, timezone

from app.usage.store import UsageLogEntry, UsageStore


def _entry(**overrides) -> UsageLogEntry:
    base = {
        "request_id": "r1",
        "timestamp": datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc),
        "team_id": "team-alpha",
        "feature": "support-bot",
        "model": "stub-fast",
        "provider": "stub",
        "input_tokens": 100,
        "output_tokens": 50,
        "latency_ms": 10.0,
        "status": "ok",
        "cost_usd": 0.5,
    }
    base.update(overrides)
    return UsageLogEntry(**base)


def test_log_and_all():
    store = UsageStore()
    store.log(_entry())
    assert len(store.all()) == 1


def test_spend_today_filters_by_date():
    store = UsageStore()
    store.log(_entry(request_id="r1", timestamp=datetime(2026, 6, 15, 8, tzinfo=timezone.utc), cost_usd=1.0))
    store.log(_entry(request_id="r2", timestamp=datetime(2026, 6, 14, 8, tzinfo=timezone.utc), cost_usd=5.0))
    now = datetime(2026, 6, 15, 20, tzinfo=timezone.utc)
    assert store.spend_today("team", "team-alpha", now) == 1.0


def test_spend_month_filters_by_month():
    store = UsageStore()
    store.log(_entry(request_id="r1", timestamp=datetime(2026, 6, 1, tzinfo=timezone.utc), cost_usd=2.0))
    store.log(_entry(request_id="r2", timestamp=datetime(2026, 5, 30, tzinfo=timezone.utc), cost_usd=9.0))
    now = datetime(2026, 6, 20, tzinfo=timezone.utc)
    assert store.spend_month("team", "team-alpha", now) == 2.0


def test_spend_scoped_by_feature_not_team():
    store = UsageStore()
    store.log(_entry(request_id="r1", team_id="team-alpha", feature="support-bot", cost_usd=3.0))
    store.log(_entry(request_id="r2", team_id="team-beta", feature="other-feature", cost_usd=4.0))
    now = datetime(2026, 6, 15, 20, tzinfo=timezone.utc)
    assert store.spend_today("feature", "support-bot", now) == 3.0
    assert store.spend_today("feature", "other-feature", now) == 4.0


def test_spend_by_team_feature_model_aggregates():
    store = UsageStore()
    store.log(_entry(request_id="r1", team_id="team-alpha", feature="a", model="m1", cost_usd=1.0))
    store.log(_entry(request_id="r2", team_id="team-alpha", feature="b", model="m2", cost_usd=2.0))
    assert store.spend_by_team() == {"team-alpha": 3.0}
    assert store.spend_by_feature() == {"a": 1.0, "b": 2.0}
    assert store.spend_by_model() == {"m1": 1.0, "m2": 2.0}
