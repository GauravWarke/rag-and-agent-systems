import pytest

from app.judge.client import OpenAIJudgeClient, StubJudgeClient
from app.policies.store import PolicyStore

_POLICIES = PolicyStore.load("data/policies.yaml")


def test_stub_flags_known_trigger():
    client = StubJudgeClient()
    policy = _POLICIES.get("toxic_language")
    verdict = client.review(policy, "prompt", "You're an idiot for asking that.")
    assert verdict.violation is True
    assert verdict.evidence == "idiot"
    assert 0.0 <= verdict.confidence <= 1.0


def test_stub_no_violation_on_clean_text():
    client = StubJudgeClient()
    policy = _POLICIES.get("toxic_language")
    verdict = client.review(policy, "prompt", "Have a wonderful day!")
    assert verdict.violation is False


def test_stub_is_deterministic():
    client = StubJudgeClient()
    policy = _POLICIES.get("unsupported_factual_claims")
    output = "This is guaranteed to work every time."
    v1 = client.review(policy, "prompt", output)
    v2 = client.review(policy, "prompt", output)
    assert v1 == v2


def test_openai_client_requires_api_key():
    client = OpenAIJudgeClient(api_key="")
    policy = _POLICIES.get("toxic_language")
    with pytest.raises(RuntimeError):
        client.review(policy, "prompt", "output")
