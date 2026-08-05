from app.judge.client import JudgeClient, JudgeVerdict
from app.judge.review import PolicyJudge
from app.policies.store import PolicyStore

_POLICIES = PolicyStore.load("data/policies.yaml")


class _ScriptedClient(JudgeClient):
    """Test double returning pre-scripted verdicts, one per call."""

    name = "scripted"

    def __init__(self, verdicts: list[JudgeVerdict]) -> None:
        self._verdicts = list(verdicts)
        self.calls = 0

    def review(self, policy, prompt, output) -> JudgeVerdict:
        verdict = self._verdicts[self.calls]
        self.calls += 1
        return verdict


def test_no_violation_produces_no_finding():
    client = _ScriptedClient([JudgeVerdict(violation=False)] * len(_POLICIES.by_strategy("llm_judge")))
    judge = PolicyJudge(_POLICIES, client)
    findings = judge.review("prompt", "clean output")
    assert findings == []


def test_low_severity_violation_needs_single_pass():
    # unsupported_factual_claims is medium severity -> no dual pass.
    verdicts = []
    for policy in _POLICIES.by_strategy("llm_judge"):
        if policy.id == "unsupported_factual_claims":
            verdicts.append(JudgeVerdict(violation=True, severity="medium", evidence="fact", confidence=0.8))
        else:
            verdicts.append(JudgeVerdict(violation=False))
    client = _ScriptedClient(verdicts)
    judge = PolicyJudge(_POLICIES, client)
    findings = judge.review("prompt", "output")
    matching = [f for f in findings if f.policy_id == "unsupported_factual_claims"]
    assert len(matching) == 1
    assert client.calls == len(verdicts)  # single pass per policy


def test_high_severity_agreement_produces_single_finding():
    policies = _POLICIES.by_strategy("llm_judge")
    verdicts = []
    for policy in policies:
        if policy.id == "toxic_language":
            # High severity -> dual pass, so two identical verdicts are consumed back-to-back.
            verdicts.append(JudgeVerdict(violation=True, severity="high", evidence="x", confidence=0.9))
            verdicts.append(JudgeVerdict(violation=True, severity="high", evidence="x", confidence=0.9))
        else:
            verdicts.append(JudgeVerdict(violation=False))
    client = _ScriptedClient(verdicts)
    judge = PolicyJudge(_POLICIES, client)
    findings = judge.review("prompt", "output")
    matching = [f for f in findings if f.policy_id == "toxic_language"]
    assert len(matching) == 1
    assert matching[0].recommended_action == "block"


def test_high_severity_disagreement_routes_to_human_review():
    client = _ScriptedClient(
        [
            JudgeVerdict(violation=True, severity="high", evidence="x", confidence=0.9),
            JudgeVerdict(violation=False, confidence=0.6),
        ]
    )
    policy = _POLICIES.get("toxic_language")
    judge = PolicyJudge(_POLICIES, client)
    findings = judge._review_policy(policy, "prompt", "output")
    assert len(findings) == 1
    assert findings[0].recommended_action == "human_review"


def test_skip_categories_are_not_judged():
    client = _ScriptedClient([JudgeVerdict(violation=False)] * 20)
    judge = PolicyJudge(_POLICIES, client)
    judge.review("prompt", "output", skip_categories={"factual_accuracy", "toxicity", "safety", "overconfidence", "brand"})
    assert client.calls == 0
