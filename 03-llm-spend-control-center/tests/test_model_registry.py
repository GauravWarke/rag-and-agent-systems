import pytest

from app.registry.models import ModelRegistry, estimate_cost


@pytest.fixture()
def registry() -> ModelRegistry:
    return ModelRegistry.load("data/model_registry.yaml")


def test_get_known_model(registry: ModelRegistry):
    spec = registry.get("stub-fast")
    assert spec.provider == "stub"
    assert spec.quality_tier == 1


def test_get_unknown_model_raises(registry: ModelRegistry):
    with pytest.raises(KeyError):
        registry.get("does-not-exist")


def test_default_for_tier_picks_cheapest(registry: ModelRegistry):
    cheapest = registry.default_for_tier(1)
    tier_1_models = registry.models_for_tier(1)
    assert cheapest.input_cost_per_million == min(m.input_cost_per_million for m in tier_1_models)


def test_default_for_tier_missing_tier_raises(registry: ModelRegistry):
    with pytest.raises(KeyError):
        registry.default_for_tier(99)


def test_default_for_tier_filters_by_available_providers(registry: ModelRegistry):
    # llama3-local (tier 1, provider ollama) is priced free, so it would
    # otherwise win on cost — but routing must not pick a provider that
    # isn't configured/available.
    picked = registry.default_for_tier(1, available_providers={"stub"})
    assert picked.provider == "stub"


def test_default_for_tier_raises_when_no_provider_available(registry: ModelRegistry):
    with pytest.raises(KeyError):
        registry.default_for_tier(1, available_providers={"does-not-exist"})


def test_estimate_cost_is_proportional(registry: ModelRegistry):
    spec = registry.get("stub-fast")
    cost = estimate_cost(spec, input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost == pytest.approx(spec.input_cost_per_million + spec.output_cost_per_million)
