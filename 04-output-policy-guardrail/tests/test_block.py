from app.core.models import Finding
from app.rewrite.block import build_block


def _finding(policy_id: str, action: str) -> Finding:
    return Finding(
        policy_id=policy_id,
        category="safety",
        severity="critical",
        detector="deterministic",
        confidence=1.0,
        evidence="",
        message="internal policy description that should not leak",
        recommended_action=action,
    )


def test_block_collects_only_block_reason_codes():
    findings = [
        _finding("unsafe_instructions", "block"),
        _finding("brand_voice_violation", "approve_with_warning"),
    ]
    result = build_block(findings)
    assert result.reason_codes == ["unsafe_instructions"]


def test_block_message_is_generic_and_does_not_echo_finding_text():
    findings = [_finding("unsafe_instructions", "block")]
    result = build_block(findings)
    assert "internal policy description" not in result.message


def test_block_reason_codes_are_deduplicated_and_sorted():
    findings = [_finding("toxic_language", "block"), _finding("toxic_language", "block"), _finding("unsafe_instructions", "block")]
    result = build_block(findings)
    assert result.reason_codes == ["toxic_language", "unsafe_instructions"]
