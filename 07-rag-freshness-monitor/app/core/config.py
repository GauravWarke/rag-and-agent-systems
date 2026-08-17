"""Application configuration, loaded from environment (secure: no secrets in source)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"

    docs_dir: str = "data/docs"
    docs_meta_path: str = "data/docs_meta.json"
    manifest_path: str = "data/index/manifest.json"
    probes_path: str = "data/probes.json"

    embedding_model: str = "stub"
    embedding_version: str = "stub-v1"
    chunking_strategy: str = "heading"

    semantic_change_epsilon: float = 0.02

    rate_limit_per_minute: int = 60


settings = Settings()
