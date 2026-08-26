from app.core.models import ConfidenceLevel
from app.ocr.confidence import estimate_confidence
from app.ocr.models import OcrResult


def test_empty_text_is_low_confidence():
    result = OcrResult(text="", lines=[], engine="stub")
    assessment = estimate_confidence(result, 800, 1000)
    assert assessment.level == ConfidenceLevel.LOW
    assert assessment.score == 0.0
    assert "no text" in assessment.reasons[0]


def test_clean_dense_text_with_high_engine_confidence_is_high():
    text = "Invoice Number: INV-1002\nVendor: Acme Corp\nTotal: $108.00\n" * 3
    result = OcrResult(text=text, lines=[], engine="tesseract", raw_confidence=92.0)
    # Small page so text density clears the threshold too (this OCR text is
    # short relative to a full-size 800x1000 scan).
    assessment = estimate_confidence(result, 300, 300)
    assert assessment.level == ConfidenceLevel.HIGH
    assert assessment.score > 0.6


def test_low_alphanumeric_ratio_lowers_confidence():
    noisy = "!@#$ %^&* ()_+ -=[] {}|; ':\",./<>?"
    result = OcrResult(text=noisy, lines=[], engine="tesseract", raw_confidence=80.0)
    assessment = estimate_confidence(result, 800, 1000)
    assert any("alphanumeric" in r for r in assessment.reasons)
    assert assessment.level != ConfidenceLevel.HIGH


def test_low_engine_confidence_is_flagged():
    result = OcrResult(text="some reasonably long recognizable text here", lines=[], engine="tesseract", raw_confidence=20.0)
    assessment = estimate_confidence(result, 800, 1000)
    assert any("low engine confidence" in r for r in assessment.reasons)
    assert assessment.level == ConfidenceLevel.LOW
