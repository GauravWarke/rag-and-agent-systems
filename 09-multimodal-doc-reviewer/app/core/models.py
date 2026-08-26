"""Shared enums for the document intake pipeline."""
from __future__ import annotations

from enum import Enum


class DocumentType(str, Enum):
    INVOICE = "invoice"
    RECEIPT = "reimbursement_receipt"
    INSURANCE_CLAIM = "insurance_claim"
    ONBOARDING_FORM = "onboarding_form"
    CONTRACT_SUMMARY = "contract_summary"
    UNKNOWN = "unknown"


class PageSourceFormat(str, Enum):
    IMAGE = "image"  # PNG / JPEG / TIFF page, rasterized as-is
    PDF_TEXT = "pdf_text"  # born-digital PDF page with an embedded text layer
    PDF_IMAGE = "pdf_image"  # PDF page with no embedded text (scanned)


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
