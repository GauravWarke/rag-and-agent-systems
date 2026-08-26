"""OCR engine abstraction (Phase 2, step 1).

`OCR_ENGINE=auto` (the default) uses `pytesseract` when the `tesseract`
binary is on PATH; otherwise it falls back to the offline `stub` engine,
which returns an empty, zero-confidence result so the pipeline routes the
page to vision fallback instead of silently returning nothing useful.
Force `OCR_ENGINE=stub` for deterministic offline demos/tests, or
`OCR_ENGINE=tesseract` to require the real engine.
"""
from __future__ import annotations

import io
import shutil

from app.core.config import settings
from app.ocr.models import OcrLine, OcrResult


def tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def _run_stub(image_png: bytes) -> OcrResult:
    return OcrResult(text="", lines=[], engine="stub", raw_confidence=None)


def _run_tesseract(image_png: bytes) -> OcrResult:
    import pytesseract
    from PIL import Image

    image = Image.open(io.BytesIO(image_png))
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    lines_by_number: dict[int, list[str]] = {}
    confidences: list[float] = []
    for word, conf, line_no in zip(data["text"], data["conf"], data["line_num"]):
        word = word.strip()
        if not word:
            continue
        lines_by_number.setdefault(line_no, []).append(word)
        try:
            score = float(conf)
        except (TypeError, ValueError):
            score = -1.0
        if score >= 0:
            confidences.append(score)

    ocr_lines = [
        OcrLine(line_number=number, text=" ".join(words))
        for number, words in sorted(lines_by_number.items())
    ]
    full_text = "\n".join(line.text for line in ocr_lines)
    mean_confidence = sum(confidences) / len(confidences) if confidences else None
    return OcrResult(text=full_text, lines=ocr_lines, engine="tesseract", raw_confidence=mean_confidence)


def run_ocr(image_png: bytes) -> OcrResult:
    engine = settings.ocr_engine
    if engine == "stub":
        return _run_stub(image_png)
    if engine == "tesseract":
        return _run_tesseract(image_png)
    if tesseract_available():
        return _run_tesseract(image_png)
    return _run_stub(image_png)
