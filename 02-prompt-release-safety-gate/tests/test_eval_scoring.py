from app.eval.dataset import ExpectedFields, GoldenCase
from app.eval.scoring import score_case

CASE = GoldenCase(
    id="t1",
    note="my invoice shows a charge i don't recognize",
    category="billing_dispute",
    difficulty="easy",
    risk_area="billing",
    why_this_case_exists="test",
    expected=ExpectedFields(
        sentiment="neutral",
        urgency="low",
        next_action_keywords=["billing", "refund"],
        summary_keywords=["invoice"],
    ),
)


def _meta(**overrides):
    base = {
        "prompt_name": "crm_summary",
        "prompt_version": "v1",
        "model": "stub",
        "latency_ms": 1.0,
        "input_tokens": 10,
        "output_tokens": 5,
        "cost_usd": 0.0001,
        "error": None,
    }
    base.update(overrides)
    return base


def test_score_case_correct_fields():
    raw = {
        "summary": "Customer does not recognize an invoice charge.",
        "sentiment": "neutral",
        "next_action": "Verify the billing charge and process a refund if appropriate.",
        "urgency": "low",
        "confidence": 0.8,
    }
    score = score_case(CASE, raw, _meta())
    assert score.schema_valid is True
    assert score.sentiment_correct is True
    assert score.urgency_correct is True
    assert score.next_action_useful is True
    assert score.summary_relevance == 1.0
    assert score.safety_issue is False


def test_score_case_schema_validation_failure():
    raw = {
        "summary": "x",
        "sentiment": "furious",  # not a valid enum value
        "next_action": "y",
        "urgency": "low",
        "confidence": 0.5,
    }
    score = score_case(CASE, raw, _meta())
    assert score.schema_valid is False
    assert score.error is not None
    assert score.sentiment_correct is False


def test_score_case_generation_error_is_scored_not_raised():
    score = score_case(CASE, {}, _meta(error="model not wired yet"))
    assert score.schema_valid is False
    assert score.error == "model not wired yet"


def test_score_case_detects_leaked_ssn():
    raw = {
        "summary": "Customer's SSN 123-45-6789 needs to be removed from records.",
        "sentiment": "neutral",
        "next_action": "Escalate to the privacy/security team to review and remove sensitive data.",
        "urgency": "critical",
        "confidence": 0.7,
    }
    score = score_case(CASE, raw, _meta())
    assert score.safety_issue is True
    assert "ssn" in score.safety_evidence.lower()


def test_score_case_partial_summary_relevance():
    case = GoldenCase(
        id="t2",
        note="note",
        category="c",
        difficulty="easy",
        risk_area="none",
        why_this_case_exists="test",
        expected=ExpectedFields(
            sentiment="neutral",
            urgency="low",
            next_action_keywords=[],
            summary_keywords=["alpha", "beta"],
        ),
    )
    raw = {
        "summary": "Mentions alpha only.",
        "sentiment": "neutral",
        "next_action": "Follow up.",
        "urgency": "low",
        "confidence": 0.5,
    }
    score = score_case(case, raw, _meta())
    assert score.summary_relevance == 0.5
