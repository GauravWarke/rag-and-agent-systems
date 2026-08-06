from app.core.models import Finding
from app.review.resolve import resolve_output


def _finding(policy_id: str, category: str, action: str, evidence: str = "") -> Finding:
    return Finding(
        policy_id=policy_id,
        category=category,
        severity="high",
        detector="deterministic",
        confidence=1.0,
        evidence=evidence,
        message="m",
        recommended_action=action,
    )


def test_approve_passes_output_through_unchanged():
    resolved = resolve_output("hello", "approve", [], None)
    assert resolved.final_output == "hello"
    assert resolved.reason_codes == []


def test_approve_with_warning_passes_output_through_unchanged():
    resolved = resolve_output("hello", "approve_with_warning", [], None)
    assert resolved.final_output == "hello"


def test_rewrite_returns_the_rewritten_text_and_applied_policy_ids():
    finding = _finding("pii_leakage", "pii", "rewrite", evidence="jane@example.com")
    resolved = resolve_output("Email jane@example.com", "rewrite", [finding], None)
    assert resolved.final_output == "Email [REDACTED]"
    assert resolved.reason_codes == ["pii_leakage"]


def test_block_withholds_output_and_returns_reason_codes():
    finding = _finding("unsafe_instructions", "safety", "block")
    resolved = resolve_output("dangerous text", "block", [finding], None)
    assert resolved.final_output is None
    assert resolved.reason_codes == ["unsafe_instructions"]


def test_human_review_withholds_output_and_returns_reason_codes():
    finding = _finding("toxic_language", "toxicity", "human_review")
    resolved = resolve_output("ambiguous text", "human_review", [finding], None)
    assert resolved.final_output is None
    assert resolved.reason_codes == ["toxic_language"]
