import pytest

from app.core.config import settings
from app.ocr.vision_fallback import run_vision_fallback


def test_offline_stub_flags_for_manual_review(monkeypatch):
    monkeypatch.setattr(settings, "vision_api_key", "")
    result = run_vision_fallback(b"fake-image-bytes", hint_text="partial ocr text")
    assert result.provider == "stub"
    assert result.text == "partial ocr text"
    assert "VISION_API_KEY" in result.note


def test_real_provider_not_wired_raises(monkeypatch):
    monkeypatch.setattr(settings, "vision_api_key", "sk-test-key")
    with pytest.raises(NotImplementedError):
        run_vision_fallback(b"fake-image-bytes")
