from app.core.models import ChatMessage
from app.providers.stub import StubAdapter


def test_stub_complete_returns_normalized_result():
    adapter = StubAdapter()
    messages = [
        ChatMessage(role="system", content="You are helpful."),
        ChatMessage(role="user", content="What is the refund policy?"),
    ]
    result = adapter.complete(messages, model="stub-fast", max_tokens=100, temperature=0.5)

    assert "stub-fast" in result.output
    assert "refund policy" in result.output
    assert result.input_tokens > 0
    assert result.output_tokens > 0
    assert result.latency_ms >= 0
    assert result.raw_metadata["provider"] == "stub"


def test_stub_complete_is_deterministic():
    adapter = StubAdapter()
    messages = [ChatMessage(role="user", content="Same question twice")]
    first = adapter.complete(messages, model="stub-fast", max_tokens=50, temperature=0.0)
    second = adapter.complete(messages, model="stub-fast", max_tokens=50, temperature=0.0)
    assert first.output == second.output


def test_stub_complete_respects_max_tokens_budget():
    adapter = StubAdapter()
    messages = [ChatMessage(role="user", content="x" * 500)]
    result = adapter.complete(messages, model="stub-fast", max_tokens=5, temperature=0.0)
    assert len(result.output) <= 5 * 4
