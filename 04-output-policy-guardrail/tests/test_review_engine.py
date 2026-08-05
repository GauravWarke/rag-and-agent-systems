from app.core.models import ReviewRequest
from app.judge.client import StubJudgeClient
from app.judge.review import PolicyJudge
from app.policies.store import PolicyStore
from app.review.engine import ReviewEngine
from app.validators.forbidden import ForbiddenTermsStore

_POLICIES = PolicyStore.load("data/policies.yaml")
_FORBIDDEN = ForbiddenTermsStore.load("data/forbidden_terms.yaml")


def _engine() -> ReviewEngine:
    judge = PolicyJudge(_POLICIES, StubJudgeClient())
    return ReviewEngine(_POLICIES, _FORBIDDEN, judge)


def test_clean_output_is_approved():
    req = ReviewRequest(prompt="What's the weather?", output="It's sunny today.", feature="weather-bot")
    resp = _engine().review(req)
    assert resp.decision == "approve"
    assert resp.findings == []


def test_pii_leak_triggers_rewrite():
    req = ReviewRequest(
        prompt="Who do I contact?",
        output="Reach out to jane.doe@example.com for help.",
        feature="support-bot",
    )
    resp = _engine().review(req)
    assert resp.decision == "rewrite"
    assert any(f.policy_id == "pii_leakage" for f in resp.findings)


def test_forbidden_content_triggers_block_without_calling_judge():
    req = ReviewRequest(prompt="Insult me", output="Well, shut up and listen.", feature="chat-bot")
    resp = _engine().review(req)
    assert resp.decision == "block"
    matching = [f for f in resp.findings if f.policy_id == "toxic_language"]
    assert len(matching) == 1
    assert matching[0].detector == "deterministic"


def test_schema_mismatch_triggers_rewrite():
    req = ReviewRequest(
        prompt="Return structured answer",
        output='{"answer": "yes"}',
        feature="qa-bot",
        expected_schema={"answer": "str", "confidence": "float"},
    )
    resp = _engine().review(req)
    assert resp.decision == "rewrite"
    assert any(f.policy_id == "schema_mismatch" for f in resp.findings)


def test_allowed_pii_types_are_not_flagged():
    req = ReviewRequest(
        prompt="Confirm my email",
        output="Confirmed: jane.doe@example.com",
        feature="account-bot",
        allowed_pii_types=["email"],
    )
    resp = _engine().review(req)
    assert resp.decision == "approve"


def test_aggregate_picks_most_severe_action():
    from app.core.models import Finding
    from app.review.engine import ReviewEngine as Engine

    findings = [
        Finding(
            policy_id="a", category="c", severity="low", detector="deterministic",
            confidence=1.0, evidence="", message="m", recommended_action="approve_with_warning",
        ),
        Finding(
            policy_id="b", category="c", severity="high", detector="deterministic",
            confidence=1.0, evidence="", message="m", recommended_action="block",
        ),
    ]
    assert Engine._aggregate(findings) == "block"
