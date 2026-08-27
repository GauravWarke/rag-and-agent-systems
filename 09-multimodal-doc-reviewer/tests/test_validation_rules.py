from app.core.models import DocumentType
from app.validation.rules import parse_date, validate_business_rules, validate_type


def _sourced(value, page_number=1, source="ocr"):
    return {"value": value, "page_number": page_number, "source": source}


def test_parse_date_accepts_multiple_formats():
    assert parse_date("2026-01-05").isoformat() == "2026-01-05"
    assert parse_date("01/05/2026").isoformat() == "2026-01-05"
    assert parse_date("January 5, 2026").isoformat() == "2026-01-05"


def test_parse_date_rejects_garbage():
    assert parse_date("not a date") is None


def test_validate_type_flags_missing_required_field():
    fields = {"vendor": _sourced("Acme Corp"), "invoice_number": _sourced("INV-1")}
    issues = validate_type(DocumentType.INVOICE, fields)
    messages = {i.field for i in issues}
    assert "invoice_date" in messages
    assert "total" in messages
    assert all(i.severity == "error" for i in issues)


def test_validate_type_flags_unparseable_date():
    fields = {
        "vendor": _sourced("Acme Corp"),
        "invoice_number": _sourced("INV-1"),
        "invoice_date": _sourced("not-a-date"),
        "total": _sourced(10.0),
    }
    issues = validate_type(DocumentType.INVOICE, fields)
    assert any(i.field == "invoice_date" and i.severity == "error" for i in issues)


def test_validate_type_passes_complete_invoice():
    fields = {
        "vendor": _sourced("Acme Corp"),
        "invoice_number": _sourced("INV-1"),
        "invoice_date": _sourced("2026-01-05"),
        "total": _sourced(108.0),
    }
    assert validate_type(DocumentType.INVOICE, fields) == []


def test_business_rule_invoice_total_mismatch():
    fields = {"subtotal": _sourced(100.0), "tax": _sourced(8.0), "total": _sourced(200.0)}
    issues = validate_business_rules(DocumentType.INVOICE, fields)
    assert any(i.field == "total" and i.severity == "error" for i in issues)


def test_business_rule_invoice_total_matches():
    fields = {
        "vendor": _sourced("Acme Corp"),
        "subtotal": _sourced(100.0),
        "tax": _sourced(8.0),
        "total": _sourced(108.0),
    }
    issues = validate_business_rules(DocumentType.INVOICE, fields)
    assert issues == []


def test_business_rule_unknown_vendor_is_warning_not_error():
    fields = {"subtotal": _sourced(10.0), "tax": _sourced(1.0), "total": _sourced(11.0), "vendor": _sourced("Shell Co")}
    issues = validate_business_rules(DocumentType.INVOICE, fields)
    assert len(issues) == 1
    assert issues[0].severity == "warning"
    assert issues[0].field == "vendor"


def test_business_rule_claim_outside_policy_window():
    fields = {"incident_date": _sourced("2026-01-01"), "claim_date": _sourced("2026-06-01")}
    issues = validate_business_rules(DocumentType.INSURANCE_CLAIM, fields)
    assert any(i.field == "claim_date" and i.severity == "error" for i in issues)


def test_business_rule_claim_before_incident_is_flagged():
    fields = {"incident_date": _sourced("2026-02-01"), "claim_date": _sourced("2026-01-01")}
    issues = validate_business_rules(DocumentType.INSURANCE_CLAIM, fields)
    assert any(i.field == "claim_date" and "before" in i.message for i in issues)


def test_business_rule_claim_within_window_is_clean():
    fields = {"incident_date": _sourced("2026-01-01"), "claim_date": _sourced("2026-01-15")}
    assert validate_business_rules(DocumentType.INSURANCE_CLAIM, fields) == []
