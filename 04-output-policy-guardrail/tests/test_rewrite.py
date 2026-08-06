from app.core.models import Finding
from app.rewrite.rewrite import apply_rewrite


def _finding(category: str, evidence: str = "", action: str = "rewrite") -> Finding:
    return Finding(
        policy_id=f"{category}_policy",
        category=category,
        severity="medium",
        detector="deterministic",
        confidence=1.0,
        evidence=evidence,
        message="m",
        recommended_action=action,
    )


def test_pii_finding_redacts_the_evidence_span():
    output = "Reach out to jane.doe@example.com for help."
    finding = _finding("pii", evidence="jane.doe@example.com")
    result = apply_rewrite(output, [finding], None)
    assert "jane.doe@example.com" not in result.text
    assert "[REDACTED]" in result.text
    assert result.applied_policy_ids == ["pii_policy"]
    assert result.fully_resolved


def test_structural_finding_fills_missing_field_with_type_default():
    output = '{"answer": "yes"}'
    finding = _finding("structural")
    result = apply_rewrite(output, [finding], {"answer": "str", "confidence": "float"})
    assert '"confidence": 0.0' in result.text
    assert result.fully_resolved


def test_structural_finding_coerces_wrong_typed_field():
    output = '{"answer": "yes", "confidence": "high"}'
    finding = _finding("structural")
    result = apply_rewrite(output, [finding], {"answer": "str", "confidence": "float"})
    assert '"confidence": 0.0' in result.text


def test_structural_finding_is_unresolved_when_not_valid_json():
    output = "not json at all"
    finding = _finding("structural")
    result = apply_rewrite(output, [finding], {"answer": "str"})
    assert result.text == output
    assert result.applied_policy_ids == []
    assert not result.fully_resolved


def test_overconfidence_finding_softens_absolute_language():
    output = "You definitely have the flu, just take ibuprofen."
    finding = _finding("overconfidence")
    result = apply_rewrite(output, [finding], None)
    assert "definitely" not in result.text.lower()
    assert result.fully_resolved


def test_unknown_category_is_left_unresolved():
    output = "some toxic text"
    finding = _finding("toxicity")
    result = apply_rewrite(output, [finding], None)
    assert result.text == output
    assert not result.fully_resolved


def test_non_rewrite_findings_are_ignored():
    output = "clean text"
    finding = _finding("pii", evidence="clean", action="approve_with_warning")
    result = apply_rewrite(output, [finding], None)
    assert result.text == output
    assert result.applied_policy_ids == []
    assert result.fully_resolved
