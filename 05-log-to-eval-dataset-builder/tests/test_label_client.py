from datetime import datetime, timezone

from app.core.models import LogEntry
from app.labels.client import StubLabelClient


def _log(**overrides) -> LogEntry:
    defaults = {
        "id": "log-1",
        "timestamp": datetime.now(timezone.utc),
        "feature": "crm_note_summary",
        "prompt": "Customer reports billing charged twice.",
        "response": "Summary: billing double-charge reported, next action: refund review.",
        "model": "gpt-4o-mini",
        "latency_ms": 200.0,
        "input_tokens": 50,
        "output_tokens": 20,
        "user_feedback": "positive",
    }
    defaults.update(overrides)
    return LogEntry(**defaults)


def test_stub_proposes_golden_answer_uses_response():
    client = StubLabelClient()
    label = client.propose(_log(), "golden_answer")
    assert label.eval_type == "golden_answer"
    assert label.expected_behavior == _log().response
    assert 0.0 <= label.confidence <= 1.0


def test_stub_proposes_expected_refusal():
    client = StubLabelClient()
    label = client.propose(_log(safety_flag=True), "expected_refusal")
    assert label.eval_type == "expected_refusal"
    assert "decline" in label.key_assertions[0].lower() or "refuse" in label.expected_behavior.lower()


def test_stub_proposes_rubric_with_scoring_text():
    client = StubLabelClient()
    label = client.propose(_log(), "rubric")
    assert label.eval_type == "rubric"
    assert label.rubric is not None
    assert label.forbidden_assertions
