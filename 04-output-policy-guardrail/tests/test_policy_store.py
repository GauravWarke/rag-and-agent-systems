from app.policies.store import PolicyStore


def test_load_reads_yaml():
    store = PolicyStore.load("data/policies.yaml")
    policy = store.get("pii_leakage")
    assert policy is not None
    assert policy.severity == "high"
    assert policy.recommended_action == "rewrite"


def test_unknown_policy_returns_none():
    store = PolicyStore.load("data/policies.yaml")
    assert store.get("does-not-exist") is None


def test_by_strategy_includes_both():
    store = PolicyStore.load("data/policies.yaml")
    deterministic = {p.id for p in store.by_strategy("deterministic")}
    assert "pii_leakage" in deterministic
    assert "toxic_language" in deterministic  # strategy "both"

    llm_judge = {p.id for p in store.by_strategy("llm_judge")}
    assert "unsupported_factual_claims" in llm_judge
    assert "toxic_language" in llm_judge  # strategy "both"
    assert "pii_leakage" not in llm_judge
