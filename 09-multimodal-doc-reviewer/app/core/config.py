"""Application configuration, loaded from environment (secure: no secrets in source)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"

    rate_limit_per_minute: int = 60

    # OCR engine: "auto" uses pytesseract when the tesseract binary is on
    # PATH, else falls back to the offline "stub" engine. Force "stub" for
    # deterministic offline demos/tests.
    ocr_engine: str = "auto"
    ocr_confidence_threshold: float = 0.6

    # Vision fallback provider key — leave blank to use the offline stub
    # (flags the page for manual review instead of calling a real model).
    vision_api_key: str = ""

    min_page_width_px: int = 600
    min_page_height_px: int = 600


settings = Settings()
