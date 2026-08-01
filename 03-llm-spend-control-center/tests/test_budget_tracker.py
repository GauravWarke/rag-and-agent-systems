from datetime import datetime, timezone

from app.budgets.policy import BudgetPolicy, BudgetPolicyStore
from app.budgets.tracker import BudgetTracker
from app.usage.store import UsageLogEntry, UsageStore

NOW = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)


def _log(store: UsageStore, team_id: str, feature: str, cost_usd: float) -> None:
    store.log(
        UsageLogEntry(
            request_id="r",
            timestamp=NOW,
            team_id=team_id,
            feature=feature,
            model="stub-fast",
            provider="stub",
            input_tokens=10,
            output_tokens=10,
            latency_ms=1.0,
            status="ok",
            cost_usd=cost_usd,
        )
    )


def _tracker(policies: list[BudgetPolicy], default: BudgetPolicy) -> tuple[BudgetTracker, UsageStore]:
    usage = UsageStore()
    policy_store = BudgetPolicyStore(policies, default)
    return BudgetTracker(usage, policy_store, warning_threshold_pct=80.0), usage


def test_status_ok_under_threshold():
    default = BudgetPolicy(scope="team", key="__default__", daily_limit_usd=10.0, monthly_limit_usd=100.0)
    tracker, usage = _tracker([], default)
    _log(usage, "team-alpha", "feature-x", 1.0)
    result = tracker.check("team-alpha", "feature-x", now=NOW)
    assert result.status == "ok"


def test_status_warning_at_80_percent():
    default = BudgetPolicy(scope="team", key="__default__", daily_limit_usd=10.0, monthly_limit_usd=100.0)
    tracker, usage = _tracker([], default)
    _log(usage, "team-alpha", "feature-x", 8.5)
    result = tracker.check("team-alpha", "feature-x", now=NOW)
    assert result.status == "warning"


def test_status_blocked_at_100_percent():
    default = BudgetPolicy(scope="team", key="__default__", daily_limit_usd=10.0, monthly_limit_usd=100.0)
    tracker, usage = _tracker([], default)
    _log(usage, "team-alpha", "feature-x", 10.0)
    result = tracker.check("team-alpha", "feature-x", now=NOW)
    assert result.status == "blocked"


def test_feature_policy_can_block_even_when_team_is_ok():
    team_policy = BudgetPolicy(scope="team", key="team-alpha", daily_limit_usd=100.0, monthly_limit_usd=1000.0)
    feature_policy = BudgetPolicy(scope="feature", key="feature-x", daily_limit_usd=1.0, monthly_limit_usd=10.0)
    default = BudgetPolicy(scope="team", key="__default__", daily_limit_usd=100.0, monthly_limit_usd=1000.0)
    tracker, usage = _tracker([team_policy, feature_policy], default)
    _log(usage, "team-alpha", "feature-x", 1.0)
    result = tracker.check("team-alpha", "feature-x", now=NOW)
    assert result.status == "blocked"
    assert result.scope == "feature"


def test_feature_without_policy_only_checks_team():
    default = BudgetPolicy(scope="team", key="__default__", daily_limit_usd=10.0, monthly_limit_usd=100.0)
    tracker, usage = _tracker([], default)
    _log(usage, "team-alpha", "unconfigured-feature", 1.0)
    result = tracker.check("team-alpha", "unconfigured-feature", now=NOW)
    assert result.scope == "team"
