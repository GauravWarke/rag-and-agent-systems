"""Application configuration, loaded from environment (secure: no secrets in source)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"

    # Label-generation provider key — leave blank to use the offline "stub" label client only.
    openai_api_key: str = ""

    rate_limit_per_minute: int = 60

    # Cosine similarity above which a candidate eval case is treated as a
    # near-duplicate of one already accepted into the dataset.
    dedupe_similarity_threshold: float = 0.92


settings = Settings()
