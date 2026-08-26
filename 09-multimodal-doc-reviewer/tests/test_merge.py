from app.core.models import DocumentType
from app.extraction.merge import merge_page_extractions


def test_merges_consistent_fields_across_pages_without_conflict():
    pages = [
        (1, "embedded_text", "Vendor: Acme Corp\nTotal: $100.00"),
        (2, "embedded_text", "Total: $100.00"),
    ]
    schema, conflicts = merge_page_extractions(DocumentType.INVOICE, pages)
    assert schema.vendor.value == "Acme Corp"
    assert schema.total.value == 100.0
    assert conflicts == []


def test_disagreeing_pages_produce_a_conflict_instead_of_overwriting():
    pages = [
        (1, "embedded_text", "Total: $100.00"),
        (2, "ocr", "Total: $999.00"),
    ]
    schema, conflicts = merge_page_extractions(DocumentType.INVOICE, pages)
    # First page wins the stored value...
    assert schema.total.value == 100.0
    # ...but the disagreement is recorded, not hidden.
    assert len(conflicts) == 1
    assert conflicts[0].field == "total"
    assert [v.value for v in conflicts[0].values] == [100.0, 999.0]


def test_line_items_accumulate_uniquely_across_pages():
    pages = [
        (1, "embedded_text", "Line Items:\n- Widget A\n"),
        (2, "embedded_text", "Line Items:\n- Widget A\n- Widget B\n"),
    ]
    schema, conflicts = merge_page_extractions(DocumentType.INVOICE, pages)
    assert schema.line_items == ["Widget A", "Widget B"]
    assert conflicts == []


def test_unknown_document_type_returns_none_schema():
    schema, conflicts = merge_page_extractions(DocumentType.UNKNOWN, [(1, "ocr", "some text")])
    assert schema is None
    assert conflicts == []
