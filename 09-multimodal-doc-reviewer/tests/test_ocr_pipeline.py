import io

from PIL import Image

from app.core.config import settings
from app.core.models import PageSourceFormat
from app.intake.models import Page
from app.ocr.pipeline import process_page


def _image_page_bytes(width=100, height=100):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(255, 255, 255)).save(buf, format="PNG")
    return buf.getvalue()


def test_pdf_text_page_uses_embedded_text_directly():
    page = Page(page_number=1, source_format=PageSourceFormat.PDF_TEXT, embedded_text="Invoice Number: INV-1")
    result = process_page(page)
    assert result.source == "embedded_text"
    assert result.text == "Invoice Number: INV-1"
    assert result.ocr is None


def test_pdf_image_page_routes_straight_to_vision_fallback():
    page = Page(page_number=1, source_format=PageSourceFormat.PDF_IMAGE)
    result = process_page(page)
    assert result.source == "vision_fallback"
    assert result.vision is not None
    assert result.vision.provider == "stub"


def test_image_page_with_stub_ocr_falls_back_to_vision(monkeypatch):
    monkeypatch.setattr(settings, "ocr_engine", "stub")
    page = Page(
        page_number=1,
        source_format=PageSourceFormat.IMAGE,
        width_px=100,
        height_px=100,
        normalized_image_png=_image_page_bytes(),
    )
    result = process_page(page)
    # The stub OCR engine returns no text -> zero confidence -> vision fallback.
    assert result.source == "vision_fallback"
    assert result.ocr is not None
    assert result.ocr.text == ""
    assert result.confidence is not None
    assert result.confidence.score == 0.0
