import pytest
from pydantic import ValidationError

from app.core.models import NoteSummary


def test_note_summary_accepts_valid_payload():
    summary = NoteSummary.model_validate(
        {
            "summary": "Customer wants a refund for order #123.",
            "sentiment": "negative",
            "next_action": "Process the refund.",
            "urgency": "medium",
            "confidence": 0.8,
        }
    )
    assert summary.sentiment.value == "negative"
    assert summary.urgency.value == "medium"


def test_note_summary_rejects_invalid_enum():
    with pytest.raises(ValidationError):
        NoteSummary.model_validate(
            {
                "summary": "x",
                "sentiment": "furious",  # not a valid Sentiment value
                "next_action": "y",
                "urgency": "medium",
                "confidence": 0.5,
            }
        )


def test_note_summary_rejects_out_of_range_confidence():
    with pytest.raises(ValidationError):
        NoteSummary.model_validate(
            {
                "summary": "x",
                "sentiment": "neutral",
                "next_action": "y",
                "urgency": "low",
                "confidence": 1.5,
            }
        )


def test_note_summary_rejects_empty_summary():
    with pytest.raises(ValidationError):
        NoteSummary.model_validate(
            {
                "summary": "",
                "sentiment": "neutral",
                "next_action": "y",
                "urgency": "low",
                "confidence": 0.5,
            }
        )
