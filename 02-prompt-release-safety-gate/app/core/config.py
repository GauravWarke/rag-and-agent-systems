"""Application configuration, loaded from environment (secure: no secrets in source)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"

    openai_api_key: str = ""
    anthropic_api_key: str = ""

    baseline_prompt: str = "crm_summary_v1"
    candidate_prompt: str = "crm_summary_v2"
    generation_model: str = "stub"

    schema_validity_drop_block_pct: float = 2.0
    cost_increase_block_pct: float = 20.0
    latency_increase_warn_pct: float = 20.0

    rate_limit_per_minute: int = 60


settings = Settings()
