from app.alerts.client import NullAlertClient, SlackAlertClient
from app.alerts.dispatch import dispatch_alerts
from app.alerts.rules import build_alerts
from app.core.models import FreshnessScorecard


def _scorecard(**overrides) -> FreshnessScorecard:
    base = {
        "generated_at": "t0",
        "manifest_available": True,
        "docs_changed": 0,
        "chunks_needing_reindex": 0,
        "probes_total": 20,
        "probes_drifting": 0,
        "answer_drift_checked": 20,
        "answer_drift_changed": 0,
        "stale_answer_risks": 0,
        "recommendations": [],
    }
    base.update(overrides)
    return FreshnessScorecard(**base)


def test_build_alerts_empty_for_healthy_scorecard():
    assert build_alerts(_scorecard()) == []


def test_build_alerts_flags_reindex_drift_and_stale_answers():
    card = _scorecard(chunks_needing_reindex=2, probes_drifting=1, stale_answer_risks=3)
    alerts = build_alerts(card)
    assert len(alerts) == 3
    assert any("re-indexing" in a for a in alerts)
    assert any("retrieval drift" in a for a in alerts)
    assert any("stale" in a for a in alerts)


def test_null_alert_client_records_without_network():
    client = NullAlertClient()
    assert client.send("hello") is True
    assert client.sent == ["hello"]


def test_slack_alert_client_requires_webhook_url():
    client = SlackAlertClient(webhook_url="")
    try:
        client.send("hello")
    except RuntimeError as exc:
        assert "SLACK_WEBHOOK_URL" in str(exc)
    else:
        raise AssertionError("expected RuntimeError when webhook is not configured")


def test_dispatch_alerts_healthy_scorecard_delivers_nothing():
    client = NullAlertClient()
    result = dispatch_alerts(_scorecard(), client)
    assert result.triggered == []
    assert result.delivered is True
    assert result.channel == "log"
    assert client.sent == []


def test_dispatch_alerts_records_triggered_messages_via_null_client():
    client = NullAlertClient()
    card = _scorecard(chunks_needing_reindex=1)
    result = dispatch_alerts(card, client)
    assert len(result.triggered) == 1
    assert result.delivered is True
    assert client.sent == result.triggered
