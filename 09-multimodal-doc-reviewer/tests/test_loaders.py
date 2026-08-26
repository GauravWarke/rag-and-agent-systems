import io

import pytest
from PIL import Image

from app.core.models import PageSourceFormat
from app.intake.loaders import load_pages
from tests.pdf_builder import build_text_pdf


def _png_bytes(width=800, height=1000):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(180, 180, 180)).save(buf, format="PNG")
    return buf.getvalue()


def test_rejects_unsupported_content_type():
    with pytest.raises(ValueError, match="unsupported content type"):
        load_pages(b"not a real file", content_type="text/plain")


def test_loads_a_single_image_page():
    pages = load_pages(_png_bytes(), content_type="image/png")
    assert len(pages) == 1
    page = pages[0]
    assert page.source_format == PageSourceFormat.IMAGE
    assert page.normalized_image_png is not None
    assert page.has_normalized_image is True
    assert page.preprocessing  # preprocessing pipeline ran


def test_undecodable_image_raises_value_error():
    with pytest.raises(ValueError, match="could not decode image"):
        load_pages(b"\x00\x01garbage", content_type="image/png")


def test_pdf_page_with_embedded_text_is_pdf_text():
    data = build_text_pdf(["Invoice Number: INV-1002\nTotal: $108.00"])
    pages = load_pages(data, content_type="application/pdf")
    assert len(pages) == 1
    page = pages[0]
    assert page.source_format == PageSourceFormat.PDF_TEXT
    assert "INV-1002" in page.embedded_text
    assert page.normalized_image_png is None


def test_pdf_page_without_text_is_pdf_image():
    data = build_text_pdf([""])
    pages = load_pages(data, content_type="application/pdf")
    page = pages[0]
    assert page.source_format == PageSourceFormat.PDF_IMAGE
    assert page.embedded_text is None
    assert page.normalized_image_png is None
    assert any("no embedded text layer" in w for w in page.warnings)


def test_multi_page_pdf_preserves_page_order():
    data = build_text_pdf(["Page one text", "Page two text"])
    pages = load_pages(data, content_type="application/pdf")
    assert [p.page_number for p in pages] == [1, 2]
    assert "Page one" in pages[0].embedded_text
    assert "Page two" in pages[1].embedded_text


def test_corrupt_pdf_raises_value_error():
    with pytest.raises(ValueError, match="could not decode PDF"):
        load_pages(b"%PDF-1.4 not really a pdf", content_type="application/pdf")
