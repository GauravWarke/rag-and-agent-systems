"""Document type classification (Phase 1, step 2).

Classification runs during intake, before OCR (Phase 2) has produced any
text for scanned/image pages. So the corpus it scores against is the
filename plus whatever embedded text a born-digital PDF page already has —
scanned images are classified on filename alone at this stage. That's a
reasonable v1: it's cheap, offline, and callers can always re-classify
once OCR text is available.
"""
from __future__ import annotations

from app.core.models import DocumentType
from app.intake.models import Page

_KEYWORDS: dict[DocumentType, list[str]] = {
    DocumentType.INVOICE: ["invoice", "bill to", "amount due", "invoice number", "vendor", "purchase order"],
    DocumentType.RECEIPT: ["receipt", "reimbursement", "expense", "paid", "payment method"],
    DocumentType.INSURANCE_CLAIM: ["claim", "policy number", "claimant", "insured", "incident date"],
    DocumentType.ONBOARDING_FORM: ["onboarding", "applicant", "new hire", "employee id", "start date"],
    DocumentType.CONTRACT_SUMMARY: ["contract", "agreement", "parties", "effective date", "term"],
}


def classify_document(filename: str, pages: list[Page]) -> tuple[DocumentType, float]:
    corpus_parts = [filename]
    for page in pages:
        if page.embedded_text:
            corpus_parts.append(page.embedded_text)
    corpus = " ".join(corpus_parts).lower()

    best_type = DocumentType.UNKNOWN
    best_score = 0
    for doc_type, keywords in _KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw in corpus)
        if matches > best_score:
            best_score = matches
            best_type = doc_type

    if best_score == 0:
        return DocumentType.UNKNOWN, 0.0

    confidence = min(1.0, best_score / 3)
    return best_type, round(confidence, 3)
