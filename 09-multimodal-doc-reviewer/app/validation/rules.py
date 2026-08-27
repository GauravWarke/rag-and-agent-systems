"""Type validation and business rules for extracted document fields
(Phase 4, steps 1-2).

Extraction (`app/extraction`) already guarantees numeric fields parse as
numbers and `document_type` is a real `DocumentType` enum member, since
both are enforced by Pydantic before a result ever reaches this module.
What is left to check here is what extraction cannot enforce on its own:
whether required fields actually showed up, whether date-looking fields
parse as real dates, and whether the values make business sense together
(totals that add up, claims filed inside the policy window, vendors that
are actually known to the business).
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from app.core.models import DocumentType
from app.validation.models import ValidationIssue

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
)

# Fields that must be present (with a non-null value) for a document of
# this type to be considered complete.
REQUIRED_FIELDS_BY_DOCUMENT_TYPE: dict[DocumentType, list[str]] = {
    DocumentType.INVOICE: ["vendor", "invoice_number", "invoice_date", "total"],
    DocumentType.RECEIPT: ["vendor", "purchase_date", "total"],
    DocumentType.INSURANCE_CLAIM: ["claimant_name", "policy_number", "claim_date", "incident_date", "claim_amount"],
    DocumentType.ONBOARDING_FORM: ["applicant_name", "email", "start_date"],
    DocumentType.CONTRACT_SUMMARY: ["effective_date", "contract_value"],
}

# Fields whose text value is expected to parse as a calendar date.
DATE_FIELDS_BY_DOCUMENT_TYPE: dict[DocumentType, list[str]] = {
    DocumentType.INVOICE: ["invoice_date", "due_date"],
    DocumentType.RECEIPT: ["purchase_date"],
    DocumentType.INSURANCE_CLAIM: ["claim_date", "incident_date"],
    DocumentType.ONBOARDING_FORM: ["start_date"],
    DocumentType.CONTRACT_SUMMARY: ["effective_date"],
}

# Demo vendor allowlist. A production system would back this with a
# customer/vendor master table instead of a hardcoded set.
KNOWN_VENDORS: set[str] = {
    "acme corp",
    "acme",
    "globex inc",
    "initech",
    "umbrella corp",
    "stark industries",
}

# An insurance claim must be filed within this many days of the incident.
CLAIM_POLICY_WINDOW_DAYS = 90

# Invoice subtotal + tax must equal total within this tolerance (float rounding).
_TOTAL_TOLERANCE = 0.01


def _field_value(fields: dict, name: str) -> object | None:
    entry = fields.get(name)
    if isinstance(entry, dict):
        return entry.get("value")
    return entry


def parse_date(raw: str) -> date | None:
    text = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc).date()
        except ValueError:
            continue
    return None


def validate_required_fields(document_type: DocumentType, fields: dict) -> list[ValidationIssue]:
    required = REQUIRED_FIELDS_BY_DOCUMENT_TYPE.get(document_type, [])
    issues: list[ValidationIssue] = []
    for name in required:
        if _field_value(fields, name) in (None, ""):
            issues.append(
                ValidationIssue(field=name, severity="error", message=f"required field '{name}' is missing")
            )
    return issues


def validate_date_fields(document_type: DocumentType, fields: dict) -> list[ValidationIssue]:
    date_fields = DATE_FIELDS_BY_DOCUMENT_TYPE.get(document_type, [])
    issues: list[ValidationIssue] = []
    for name in date_fields:
        value = _field_value(fields, name)
        if value is None:
            continue
        if not isinstance(value, str) or parse_date(value) is None:
            issues.append(
                ValidationIssue(field=name, severity="error", message=f"field '{name}' is not a parseable date")
            )
    return issues


def validate_type(document_type: DocumentType, fields: dict) -> list[ValidationIssue]:
    """Type validation (Phase 4, step 1): required fields exist and any
    date-looking field actually parses as a date. Numeric fields and the
    `document_type` enum are already guaranteed valid by the extraction
    schema, so there is nothing further to check for them here.
    """
    return validate_required_fields(document_type, fields) + validate_date_fields(document_type, fields)


def _check_invoice_totals(fields: dict) -> ValidationIssue | None:
    subtotal = _field_value(fields, "subtotal")
    tax = _field_value(fields, "tax")
    total = _field_value(fields, "total")
    if not isinstance(subtotal, (int, float)) or not isinstance(tax, (int, float)) or not isinstance(total, (int, float)):
        return None
    if abs((subtotal + tax) - total) > _TOTAL_TOLERANCE:
        return ValidationIssue(
            field="total",
            severity="error",
            message=f"subtotal ({subtotal}) + tax ({tax}) != total ({total})",
        )
    return None


def _check_claim_window(fields: dict) -> ValidationIssue | None:
    claim_raw = _field_value(fields, "claim_date")
    incident_raw = _field_value(fields, "incident_date")
    if not isinstance(claim_raw, str) or not isinstance(incident_raw, str):
        return None
    claim_date = parse_date(claim_raw)
    incident_date = parse_date(incident_raw)
    if claim_date is None or incident_date is None:
        return None
    if claim_date < incident_date:
        return ValidationIssue(
            field="claim_date", severity="error", message="claim date is before the incident date"
        )
    if (claim_date - incident_date).days > CLAIM_POLICY_WINDOW_DAYS:
        return ValidationIssue(
            field="claim_date",
            severity="error",
            message=f"claim filed more than {CLAIM_POLICY_WINDOW_DAYS} days after the incident",
        )
    return None


def _check_known_vendor(fields: dict) -> ValidationIssue | None:
    vendor = _field_value(fields, "vendor")
    if not isinstance(vendor, str):
        return None
    if vendor.strip().lower() not in KNOWN_VENDORS:
        return ValidationIssue(field="vendor", severity="warning", message=f"vendor '{vendor}' is not a known vendor")
    return None


def validate_business_rules(document_type: DocumentType, fields: dict) -> list[ValidationIssue]:
    """Business rules (Phase 4, step 2): cross-field checks that a type
    check alone cannot catch.
    """
    issues: list[ValidationIssue] = []

    if document_type == DocumentType.INVOICE:
        issue = _check_invoice_totals(fields)
        if issue is not None:
            issues.append(issue)

    if document_type == DocumentType.INSURANCE_CLAIM:
        issue = _check_claim_window(fields)
        if issue is not None:
            issues.append(issue)

    if document_type in (DocumentType.INVOICE, DocumentType.RECEIPT):
        issue = _check_known_vendor(fields)
        if issue is not None:
            issues.append(issue)

    return issues
