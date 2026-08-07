from pathlib import Path

from app.policies.store import PolicyStore

_POLICIES_YAML = Path("data/policies.yaml").read_text()


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


def test_from_text_matches_load():
    text_store = PolicyStore.from_text(_POLICIES_YAML)
    path_store = PolicyStore.load("data/policies.yaml")
    assert text_store.version == path_store.version


def test_from_text_with_no_policies_key_is_empty():
    store = PolicyStore.from_text("other_key: 1")
    assert store.all() == []


def test_version_changes_when_a_policy_is_edited():
    base = PolicyStore.load("data/policies.yaml")
    edited_yaml = _POLICIES_YAML.replace("recommended_action: rewrite", "recommended_action: block")
    edited = PolicyStore.from_text(edited_yaml)
    assert base.version != edited.version
