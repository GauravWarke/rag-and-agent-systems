import pytest

from app.core.models import DocFormat
from app.ingestion.normalizer import (
    load_html_file,
    load_markdown_file,
    load_pdf_file,
    load_text_file,
    normalize_document,
    save_normalized,
)


def _make_pdf(pages_text: list[str]) -> bytes:
    """Build a minimal valid single/multi-page PDF with real xref offsets,
    so `pypdf` can parse it without needing a binary fixture on disk."""
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        (
            f"<< /Type /Pages /Kids [{' '.join(f'{3 + i} 0 R' for i in range(len(pages_text)))}] "
            f"/Count {len(pages_text)} >>"
        ).encode(),
    ]
    font_obj = 3 + len(pages_text)
    for i in range(len(pages_text)):
        objects.append((
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
            f"/Resources << /Font << /F1 {font_obj} 0 R >> >> "
            f"/Contents {font_obj + 1 + i} 0 R >>"
        ).encode())
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for text in pages_text:
        escaped = text.replace("(", r"\(").replace(")", r"\)")
        stream = f"BT /F1 12 Tf 20 250 Td ({escaped}) Tj ET".encode()
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")

    buf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(buf))
        buf += f"{idx} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_offset = len(buf)
    n = len(objects) + 1
    buf += f"xref\n0 {n}\n".encode()
    buf += b"0000000000 65535 f \n"
    for off in offsets:
        buf += f"{off:010d} 00000 n \n".encode()
    buf += f"trailer\n<< /Size {n} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode()
    return bytes(buf)


def test_load_markdown_file_keeps_raw_and_cleans_whitespace(tmp_path):
    path = tmp_path / "faq.md"
    path.write_text("# Title\n\n\n\nBody text.   \n", encoding="utf-8")

    doc = load_markdown_file(path)

    assert doc.doc_format == DocFormat.markdown
    assert doc.raw_text == "# Title\n\n\n\nBody text.   \n"
    assert "# Title" in doc.cleaned_text
    assert "\n\n\n" not in doc.cleaned_text  # collapsed


def test_load_html_file_converts_headings_to_markdown(tmp_path):
    path = tmp_path / "policy.html"
    path.write_text(
        "<html><body><h1>Refund Policy</h1><p>Refunds within 30 days.</p>"
        "<h2>Exceptions</h2><p>Digital goods are final sale.</p></body></html>",
        encoding="utf-8",
    )

    doc = load_html_file(path)

    assert doc.doc_format == DocFormat.html
    assert "<h1>" in doc.raw_text
    assert "# Refund Policy" in doc.cleaned_text
    assert "## Exceptions" in doc.cleaned_text
    assert "Refunds within 30 days." in doc.cleaned_text
    assert "<p>" not in doc.cleaned_text


def test_load_text_file_normalizes_line_endings(tmp_path):
    path = tmp_path / "release.txt"
    path.write_bytes(b"Line one.\r\nLine two.\r\n\r\n\r\nLine three.\r\n")

    doc = load_text_file(path)

    assert doc.doc_format == DocFormat.text
    assert "\r" not in doc.cleaned_text
    assert "\n\n\n" not in doc.cleaned_text


def test_load_pdf_file_preserves_page_numbers(tmp_path):
    path = tmp_path / "onboarding.pdf"
    path.write_bytes(_make_pdf(["Welcome aboard.", "Step two: verify your email."]))

    doc = load_pdf_file(path)

    assert doc.doc_format == DocFormat.pdf
    assert doc.page_count == 2
    assert "## Page 1" in doc.cleaned_text
    assert "## Page 2" in doc.cleaned_text
    assert "Welcome aboard." in doc.cleaned_text
    assert "Welcome aboard." in doc.raw_text
    assert "## Page" not in doc.raw_text  # raw has no synthetic markers


def test_normalize_document_dispatches_by_extension(tmp_path):
    md = tmp_path / "a.md"
    md.write_text("# Hi", encoding="utf-8")
    assert normalize_document(md).doc_format == DocFormat.markdown

    txt = tmp_path / "a.txt"
    txt.write_text("hi", encoding="utf-8")
    assert normalize_document(txt).doc_format == DocFormat.text


def test_normalize_document_rejects_unsupported_extension(tmp_path):
    path = tmp_path / "a.docx"
    path.write_text("nope", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported"):
        normalize_document(path)


def test_save_normalized_persists_both_versions(tmp_path):
    src = tmp_path / "faq.md"
    src.write_text("# Title\n\nBody.\n", encoding="utf-8")
    doc = load_markdown_file(src)

    out_dir = tmp_path / "normalized"
    raw_path, clean_path = save_normalized(doc, out_dir)

    assert raw_path.read_text(encoding="utf-8") == doc.raw_text
    assert clean_path.read_text(encoding="utf-8") == doc.cleaned_text
