"""Structured field schemas by document type (Phase 3, step 1).

Every scalar field is wrapped in `SourcedValue` so extraction output
carries a field-level source reference (which page, and whether it came
from the document's embedded text, OCR, or vision fallback) as required
by Phase 3, step 2.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.models import DocumentType


class SourcedValue(BaseModel):
    value: str | float
    page_number: int
    source: str  # "embedded_text" | "ocr" | "vision_fallback"


class InvoiceFields(BaseModel):
    vendor: SourcedValue | None = None
    invoice_number: SourcedValue | None = None
    invoice_date: SourcedValue | None = None
    due_date: SourcedValue | None = None
    subtotal: SourcedValue | None = None
    tax: SourcedValue | None = None
    total: SourcedValue | None = None
    line_items: list[str] = Field(default_factory=list)


class ReceiptFields(BaseModel):
    vendor: SourcedValue | None = None
    purchase_date: SourcedValue | None = None
    total: SourcedValue | None = None
    payment_method: SourcedValue | None = None


class InsuranceClaimFields(BaseModel):
    claimant_name: SourcedValue | None = None
    policy_number: SourcedValue | None = None
    claim_date: SourcedValue | None = None
    incident_date: SourcedValue | None = None
    claim_amount: SourcedValue | None = None


class OnboardingFormFields(BaseModel):
    applicant_name: SourcedValue | None = None
    email: SourcedValue | None = None
    start_date: SourcedValue | None = None
    position: SourcedValue | None = None


class ContractSummaryFields(BaseModel):
    effective_date: SourcedValue | None = None
    term: SourcedValue | None = None
    contract_value: SourcedValue | None = None
    parties: list[str] = Field(default_factory=list)


FIELDS_BY_DOCUMENT_TYPE: dict[DocumentType, type[BaseModel]] = {
    DocumentType.INVOICE: InvoiceFields,
    DocumentType.RECEIPT: ReceiptFields,
    DocumentType.INSURANCE_CLAIM: InsuranceClaimFields,
    DocumentType.ONBOARDING_FORM: OnboardingFormFields,
    DocumentType.CONTRACT_SUMMARY: ContractSummaryFields,
}

# Fields whose raw text should be parsed to a number.
NUMERIC_FIELDS: set[str] = {"subtotal", "tax", "total", "claim_amount", "contract_value"}

# List-valued fields, accumulated across pages instead of conflict-checked.
LIST_FIELDS_BY_DOCUMENT_TYPE: dict[DocumentType, str] = {
    DocumentType.INVOICE: "line_items",
    DocumentType.CONTRACT_SUMMARY: "parties",
}

# Label synonyms scanned for, per document type and field, as `Label: value` lines.
LABELS_BY_DOCUMENT_TYPE: dict[DocumentType, dict[str, list[str]]] = {
    DocumentType.INVOICE: {
        "vendor": ["vendor", "supplier", "billed by", "from"],
        "invoice_number": ["invoice number", "invoice #", "invoice no"],
        "invoice_date": ["invoice date"],
        "due_date": ["due date"],
        "subtotal": ["subtotal"],
        "tax": ["tax"],
        "total": ["total", "amount due", "grand total"],
    },
    DocumentType.RECEIPT: {
        "vendor": ["vendor", "merchant", "store"],
        "purchase_date": ["purchase date", "date"],
        "total": ["total", "amount paid"],
        "payment_method": ["payment method", "paid via", "paid by"],
    },
    DocumentType.INSURANCE_CLAIM: {
        "claimant_name": ["claimant", "claimant name", "insured"],
        "policy_number": ["policy number", "policy #"],
        "claim_date": ["claim date", "date filed"],
        "incident_date": ["incident date", "date of loss"],
        "claim_amount": ["claim amount", "amount claimed"],
    },
    DocumentType.ONBOARDING_FORM: {
        "applicant_name": ["applicant name", "applicant", "full name", "name"],
        "email": ["email"],
        "start_date": ["start date"],
        "position": ["position", "job title", "role"],
    },
    DocumentType.CONTRACT_SUMMARY: {
        "effective_date": ["effective date"],
        "term": ["term"],
        "contract_value": ["contract value", "total value"],
    },
}
