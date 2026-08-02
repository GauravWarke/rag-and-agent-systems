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


def test_spend_today_total_sums_across_scopes():
    store = UsageStore()
    store.log(_entry(request_id="r1", timestamp=datetime(2026, 6, 15, 8, tzinfo=timezone.utc), cost_usd=1.0))
    store.log(_entry(request_id="r2", timestamp=datetime(2026, 6, 15, 9, tzinfo=timezone.utc), cost_usd=2.0))
    store.log(_entry(request_id="r3", timestamp=datetime(2026, 6, 14, 9, tzinfo=timezone.utc), cost_usd=5.0))
    now = datetime(2026, 6, 15, 20, tzinfo=timezone.utc)
    assert store.spend_today_total(now) == 3.0


def test_spend_month_total_sums_across_scopes():
    store = UsageStore()
    store.log(_entry(request_id="r1", timestamp=datetime(2026, 6, 1, tzinfo=timezone.utc), cost_usd=2.0))
    store.log(_entry(request_id="r2", timestamp=datetime(2026, 6, 20, tzinfo=timezone.utc), cost_usd=3.0))
    store.log(_entry(request_id="r3", timestamp=datetime(2026, 5, 30, tzinfo=timezone.utc), cost_usd=9.0))
    now = datetime(2026, 6, 20, tzinfo=timezone.utc)
    assert store.spend_month_total(now) == 5.0


def test_monthly_projection_scales_month_to_date_by_days_remaining():
    store = UsageStore()
    store.log(_entry(request_id="r1", timestamp=datetime(2026, 6, 1, tzinfo=timezone.utc), cost_usd=10.0))
    # June has 30 days; $10 spent by day 10 -> $30 projected for the month.
    now = datetime(2026, 6, 10, tzinfo=timezone.utc)
    assert store.monthly_projection(now) == 30.0


def test_top_expensive_orders_by_cost_desc_and_respects_limit():
    store = UsageStore()
    store.log(_entry(request_id="cheap", cost_usd=0.1))
    store.log(_entry(request_id="pricey", cost_usd=9.0))
    store.log(_entry(request_id="mid", cost_usd=1.0))
    top = store.top_expensive(limit=2)
    assert [e["request_id"] for e in top] == ["pricey", "mid"]
