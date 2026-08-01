"""Maps a model's `provider` field to its adapter instance."""
from __future__ import annotations

from app.core.config import settings

from .anthropic_adapter import AnthropicAdapter
from .base import ProviderAdapter
from .ollama_adapter import OllamaAdapter
from .openai_adapter import OpenAIAdapter
from .stub import StubAdapter

_ADAPTERS: dict[str, ProviderAdapter] = {
    "stub": StubAdapter(),
    "openai": OpenAIAdapter(api_key=settings.openai_api_key),
    "anthropic": AnthropicAdapter(api_key=settings.anthropic_api_key),
    "ollama": OllamaAdapter(base_url=settings.ollama_base_url),
}


def get_adapter(provider: str) -> ProviderAdapter:
    try:
        return _ADAPTERS[provider]
    except KeyError:
        raise ValueError(f"Unknown provider: {provider}") from None
