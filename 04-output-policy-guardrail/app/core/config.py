"""Application configuration, loaded from environment (secure: no secrets in source)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"

    # LLM judge provider key — leave blank to use the offline "stub" judge only.
    openai_api_key: str = ""

    # Config data files.
    policies_path: str = "data/policies.yaml"
    forbidden_terms_path: str = "data/forbidden_terms.yaml"

    rate_limit_per_minute: int = 60


settings = Settings()
