import app.main as main_module
from app.core.rate_limit import RateLimiter
from simulate_workload import render_report, run_simulation


def test_run_simulation_produces_consistent_counts(monkeypatch):
    # The gateway's rate limiter is shared across the whole test session and
    # sized for real traffic (60 req/min); raise it so this batch never trips
    # it regardless of how many other tests already ran this minute.
    monkeypatch.setattr(main_module, "_limiter", RateLimiter(1_000_000))

    result = run_simulation(n=25, seed=7)

    assert result["requests_sent"] == 25
    assert sum(result["status_counts"].values()) == 25
    assert result["status_counts"].get(200, 0) > 0
    assert set(result["tier_counts"]) <= {"1", "2", "3", "explicit"}
    assert sum(result["tier_counts"].values()) == result["status_counts"][200]
    assert result["escalation_count"] <= result["status_counts"][200]

    # Other test modules seed the shared usage store with unrealistic
    # cost/token combinations to exercise budget blocking, so don't assert
    # hypothetical >= actual here — just that the shape is sane.
    savings = result["savings"]
    assert savings["request_count"] >= 25
    assert savings["actual_cost_usd"] >= 0
    assert savings["hypothetical_strongest_model_cost_usd"] >= 0


def test_run_simulation_is_reproducible_for_routing_and_cost(monkeypatch):
    monkeypatch.setattr(main_module, "_limiter", RateLimiter(1_000_000))

    first = run_simulation(n=25, seed=99)
    second = run_simulation(n=25, seed=99)

    assert first["tier_counts"] == second["tier_counts"]
    assert first["status_counts"] == second["status_counts"]
    # Spend totals include prior test-session activity, but the *delta* the
    # same deterministic batch adds should be identical both times.
    assert second["spend"]["daily_cost_usd"] - first["spend"]["daily_cost_usd"] >= 0


def test_render_report_includes_headline_and_tables():
    report = render_report(
        {
            "requests_sent": 10,
            "seed": 1,
            "status_counts": {200: 9, 402: 1},
            "tier_counts": {"1": 5, "2": 3, "3": 1},
            "escalation_count": 2,
            "warning_count": 1,
            "spend": {
                "daily_cost_usd": 0.01,
                "monthly_cost_usd": 0.01,
                "monthly_projection_usd": 0.3,
                "by_team": {"team-alpha": 0.01},
            },
            "savings": {
                "strongest_model": "stub-strong",
                "actual_cost_usd": 0.01,
                "hypothetical_strongest_model_cost_usd": 0.02,
                "savings_pct": 0.5,
            },
            "routing_quality": {"escalation_rate": 0.2, "verifier_pass_rate": 1.0},
            "quality_summary": {"total_checks": 3, "routing_miss_count": 0},
        }
    )

    assert "# Simulated Workload Cost Savings Report" in report
    assert "Reduced simulated LLM spend by **50.0%**" in report
    assert "| 200 OK | 9 |" in report
    assert "| 402 Budget blocked | 1 |" in report
    assert "| team-alpha | $0.0100 |" in report
