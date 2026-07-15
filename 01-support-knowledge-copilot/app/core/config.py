"""Application configuration, loaded from environment (secure: no secrets in source)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"

    openai_api_key: str = ""
    anthropic_api_key: str = ""

    embedding_model: str = "stub"
    vector_store: str = "memory"
    dense_top_k: int = 20
    sparse_top_k: int = 20
    rerank_top_k: int = 5
    rrf_k: int = 60
    min_retrieval_score: float = 0.15


settings = Settings()
