from app.core.config import settings
from app.ocr.engine import run_ocr, tesseract_available


def test_stub_engine_returns_empty_zero_confidence_result(monkeypatch):
    monkeypatch.setattr(settings, "ocr_engine", "stub")
    result = run_ocr(b"")
    assert result.engine == "stub"
    assert result.text == ""
    assert result.lines == []
    assert result.raw_confidence is None


def test_auto_falls_back_to_stub_when_tesseract_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "ocr_engine", "auto")
    monkeypatch.setattr("app.ocr.engine.tesseract_available", lambda: False)
    result = run_ocr(b"")
    assert result.engine == "stub"


def test_tesseract_available_reflects_shutil_which(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/tesseract" if name == "tesseract" else None)
    assert tesseract_available() is True

    monkeypatch.setattr("shutil.which", lambda name: None)
    assert tesseract_available() is False
