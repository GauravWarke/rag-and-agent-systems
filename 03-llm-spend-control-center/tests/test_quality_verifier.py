from app.core.models import ChatMessage
from app.providers.base import ProviderResult
from app.quality.store import QualityStore
from app.quality.verifier import QualityVerifier
from app.registry.models import ModelRegistry, ModelSpec


def _registry() -> ModelRegistry:
    return ModelRegistry(
        [
            ModelSpec(
                name="cheap-model",
                provider="fake",
                quality_tier=1,
                input_cost_per_million=0.1,
                output_cost_per_million=0.1,
                latency_estimate_ms=100,
                max_context_tokens=1000,
            ),
            ModelSpec(
                name="strong-model",
                provider="fake",
                quality_tier=3,
                input_cost_per_million=5.0,
                output_cost_per_million=10.0,
                latency_estimate_ms=800,
                max_context_tokens=1000,
            ),
        ]
    )


class _FakeAdapter:
    def __init__(self, output: str) -> None:
        self._output = output

    def complete(self, messages, model, max_tokens, temperature):
        return ProviderResult(
            output=self._output,
            input_tokens=5,
            output_tokens=5,
            latency_ms=1.0,
            raw_metadata={},
        )


def _verifier(reference_output: str, quality_store: QualityStore, threshold: float = 0.5) -> QualityVerifier:
    adapter = _FakeAdapter(reference_output)
    return QualityVerifier(
        model_registry=_registry(),
        quality_store=quality_store,
        get_adapter=lambda provider: adapter,
        available_providers=lambda: {"fake"},
        similarity_threshold=threshold,
    )


def _messages() -> list[ChatMessage]:
    return [ChatMessage(role="user", content="Summarize this ticket about a billing issue.")]


def test_verify_logs_pass_when_outputs_are_similar():
    store = QualityStore()
    verifier = _verifier("Summarize this ticket about a billing issue.", store)
    verifier.verify(
        request_id="r1",
        team_id="team-alpha",
        feature="support-bot",
        messages=_messages(),
        cheap_model_name="cheap-model",
        cheap_output="Summarize this ticket about a billing issue.",
        max_tokens=100,
        temperature=0.7,
    )
    entries = store.all()
    assert len(entries) == 1
    assert entries[0].is_routing_miss is False
    assert entries[0].reference_model == "strong-model"


def test_verify_logs_miss_when_outputs_diverge():
    store = QualityStore()
    verifier = _verifier("completely unrelated response about the weather", store)
    verifier.verify(
        request_id="r1",
        team_id="team-alpha",
        feature="support-bot",
        messages=_messages(),
        cheap_model_name="cheap-model",
        cheap_output="Summarize this ticket about a billing issue.",
        max_tokens=100,
        temperature=0.7,
    )
    entries = store.all()
    assert len(entries) == 1
    assert entries[0].is_routing_miss is True
    assert entries[0].reason is not None


def test_verify_skips_when_no_stronger_model_available():
    store = QualityStore()
    verifier = QualityVerifier(
        model_registry=_registry(),
        quality_store=store,
        get_adapter=lambda provider: _FakeAdapter("anything"),
        available_providers=lambda: set(),  # no providers available at all
        similarity_threshold=0.5,
    )
    verifier.verify(
        request_id="r1",
        team_id="team-alpha",
        feature="support-bot",
        messages=_messages(),
        cheap_model_name="cheap-model",
        cheap_output="anything",
        max_tokens=100,
        temperature=0.7,
    )
    assert store.all() == []
