from app.core.models import DocumentType, PageSourceFormat
from app.intake.classifier import classify_document
from app.intake.models import Page


def _text_page(text: str) -> Page:
    return Page(page_number=1, source_format=PageSourceFormat.PDF_TEXT, embedded_text=text)


def _image_page() -> Page:
    return Page(page_number=1, source_format=PageSourceFormat.IMAGE)


def test_classifies_invoice_from_embedded_text():
    doc_type, confidence = classify_document(
        "doc.pdf", [_text_page("Invoice Number: INV-1\nAmount Due: $10\nVendor: Acme")]
    )
    assert doc_type == DocumentType.INVOICE
    assert confidence > 0


def test_classifies_receipt_from_embedded_text():
    doc_type, _ = classify_document("doc.pdf", [_text_page("Receipt\nReimbursement\nPayment Method: cash")])
    assert doc_type == DocumentType.RECEIPT


def test_falls_back_to_filename_when_no_embedded_text():
    doc_type, confidence = classify_document("insurance_claim_scan.png", [_image_page()])
    assert doc_type == DocumentType.INSURANCE_CLAIM
    assert confidence > 0


def test_unknown_when_no_keywords_match():
    doc_type, confidence = classify_document("scan001.png", [_image_page()])
    assert doc_type == DocumentType.UNKNOWN
    assert confidence == 0.0


def test_confidence_is_bounded_at_one():
    text = "invoice bill to amount due invoice number vendor purchase order"
    _, confidence = classify_document("doc.pdf", [_text_page(text)])
    assert confidence == 1.0
