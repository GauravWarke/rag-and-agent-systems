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
    rerank_candidates: int = 20
    rerank_top_k: int = 5
    rerank_model: str = "stub"
    rrf_k: int = 60
    min_retrieval_score: float = 0.15

    generation_model: str = "stub"

    rate_limit_per_minute: int = 60
    # Upper bound on distinct clients the in-memory limiter tracks at once.
    rate_limit_max_clients: int = 10_000
    # Reverse proxies in front of the app. 0 = trust the socket peer only.
    # Set to the real hop count behind a load balancer (e.g. 1 on Render/Fly).
    trusted_proxy_hops: int = 0


settings = Settings()
