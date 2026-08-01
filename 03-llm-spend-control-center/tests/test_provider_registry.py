import pytest

from app.providers.registry import get_adapter
from app.providers.stub import StubAdapter


def test_get_adapter_stub():
    adapter = get_adapter("stub")
    assert isinstance(adapter, StubAdapter)


def test_get_adapter_unknown_raises():
    with pytest.raises(ValueError):
        get_adapter("does-not-exist")


def test_openai_adapter_without_key_raises_on_complete():
    from app.core.models import ChatMessage
    from app.providers.openai_adapter import OpenAIAdapter

    adapter = OpenAIAdapter(api_key="")
    with pytest.raises(RuntimeError):
        adapter.complete([ChatMessage(role="user", content="hi")], "gpt-4o-mini", 100, 0.5)


def test_anthropic_adapter_without_key_raises_on_complete():
    from app.core.models import ChatMessage
    from app.providers.anthropic_adapter import AnthropicAdapter

    adapter = AnthropicAdapter(api_key="")
    with pytest.raises(RuntimeError):
        adapter.complete([ChatMessage(role="user", content="hi")], "claude-haiku", 100, 0.5)
