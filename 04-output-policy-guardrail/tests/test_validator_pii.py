from app.policies.store import PolicyStore
from app.validators.pii import build_pii_findings, detect_pii

_POLICY = PolicyStore.load("data/policies.yaml").get("pii_leakage")


def test_detects_email():
    hits = detect_pii("Contact me at jane.doe@example.com please.")
    assert any(t == "email" for t, _, _ in hits)


def test_detects_phone():
    hits = detect_pii("Call me at 555-123-4567 tomorrow.")
    assert any(t == "phone" for t, _, _ in hits)


def test_detects_api_key():
    hits = detect_pii("Your key is sk-liveabcdefghijklmnopqrstuvwxyz1234")
    assert any(t == "api_key" for t, _, _ in hits)


def test_detects_valid_credit_card_but_not_random_digits():
    # 4111111111111111 is a well-known Luhn-valid test Visa number.
    hits = detect_pii("Card on file: 4111111111111111")
    assert any(t == "credit_card" for t, _, _ in hits)

    hits_invalid = detect_pii("Order number: 1234567890123")
    assert not any(t == "credit_card" for t, _, _ in hits_invalid)


def test_no_pii_in_clean_text():
    hits = detect_pii("The weather is nice today.")
    assert hits == []


def test_allowed_types_are_skipped():
    hits = detect_pii("Contact jane.doe@example.com", allowed_types={"email"})
    assert hits == []


def test_build_pii_findings_returns_findings():
    findings = build_pii_findings("Email me at jane.doe@example.com", _POLICY)
    assert len(findings) == 1
    assert findings[0].policy_id == "pii_leakage"
    assert findings[0].evidence == "jane.doe@example.com"


def test_build_pii_findings_respects_allowed_types():
    findings = build_pii_findings("Email me at jane.doe@example.com", _POLICY, allowed_types=["email"])
    assert findings == []
