"""Application configuration, loaded from environment (secure: no secrets in source)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"

    # Provider keys — leave blank to use the offline "stub" provider only.
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_enabled: bool = False

    # Config data files.
    model_registry_path: str = "data/model_registry.yaml"
    budget_policies_path: str = "data/budget_policies.yaml"
    routing_overrides_path: str = "data/routing_overrides.yaml"

    # Budget enforcement thresholds.
    budget_warning_threshold_pct: float = 80.0

    rate_limit_per_minute: int = 60


settings = Settings()
