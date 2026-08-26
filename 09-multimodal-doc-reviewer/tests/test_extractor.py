from app.core.models import DocumentType
from app.extraction.extractor import extract_page_fields


def test_extracts_invoice_labeled_fields_and_line_items():
    text = (
        "Vendor: Acme Corp\n"
        "Invoice Number: INV-1002\n"
        "Invoice Date: 2026-01-05\n"
        "Due Date: 2026-02-05\n"
        "Subtotal: $100.00\n"
        "Tax: $8.00\n"
        "Total: $108.00\n"
        "Line Items:\n"
        "- Widget A - $50.00\n"
        "- Widget B - $50.00\n"
    )
    fields = extract_page_fields(DocumentType.INVOICE, text, page_number=1, source="ocr")

    assert fields["vendor"].value == "Acme Corp"
    assert fields["invoice_number"].value == "INV-1002"
    assert fields["subtotal"].value == 100.0
    assert fields["tax"].value == 8.0
    assert fields["total"].value == 108.0
    assert fields["vendor"].page_number == 1
    assert fields["vendor"].source == "ocr"
    assert fields["line_items"] == ["Widget A - $50.00", "Widget B - $50.00"]


def test_numeric_field_with_commas_parses():
    text = "Total: $1,234.56"
    fields = extract_page_fields(DocumentType.INVOICE, text, page_number=1, source="embedded_text")
    assert fields["total"].value == 1234.56


def test_unparseable_numeric_field_is_skipped():
    text = "Total: not-a-number"
    fields = extract_page_fields(DocumentType.INVOICE, text, page_number=1, source="embedded_text")
    assert "total" not in fields


def test_email_regex_fallback_for_onboarding_form():
    text = "Applicant: Jane Doe\ncontact her at jane.doe@example.com for details"
    fields = extract_page_fields(DocumentType.ONBOARDING_FORM, text, page_number=1, source="ocr")
    assert fields["email"].value == "jane.doe@example.com"


def test_contract_parties_split_on_and_and_comma():
    text = "Parties: Acme Corp, Beta LLC and Gamma Inc"
    fields = extract_page_fields(DocumentType.CONTRACT_SUMMARY, text, page_number=1, source="embedded_text")
    assert fields["parties"] == ["Acme Corp", "Beta LLC", "Gamma Inc"]


def test_unknown_document_type_returns_no_fields():
    fields = extract_page_fields(DocumentType.UNKNOWN, "some text", page_number=1, source="ocr")
    assert fields == {}
