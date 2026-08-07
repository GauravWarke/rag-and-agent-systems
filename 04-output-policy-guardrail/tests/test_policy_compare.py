from pathlib import Path

import yaml

from app.core.audit import AuditLog
from app.core.models import ReviewRequest
from app.judge.client import StubJudgeClient
from app.judge.review import PolicyJudge
from app.policies.compare import ComparisonExample, compare_policy_versions
from app.policies.store import PolicyStore
from app.review.engine import ReviewEngine
from app.validators.forbidden import ForbiddenTermsStore

_POLICIES_YAML = Path("data/policies.yaml").read_text()
_FORBIDDEN = ForbiddenTermsStore.load("data/forbidden_terms.yaml")
_BASELINE = PolicyStore.load("data/policies.yaml")


def _pii_example() -> ComparisonExample:
    return ComparisonExample(
        label="pii-email",
        prompt="Who do I contact?",
        output="Reach out to jane.doe@example.com for help.",
        feature="support-bot",
    )


def test_identical_policy_sets_produce_no_diffs():
    result = compare_policy_versions([_pii_example()], _BASELINE, _BASELINE, _FORBIDDEN, StubJudgeClient())
    assert result.changed_count == 0
    assert result.baseline_version == result.candidate_version
    assert result.diffs[0].baseline_decision == result.diffs[0].candidate_decision == "rewrite"


def test_stricter_candidate_policy_flips_decision():
    candidate_yaml = _POLICIES_YAML.replace(
        "    detection_strategy: deterministic\n    recommended_action: rewrite",
        "    detection_strategy: deterministic\n    recommended_action: block",
    )
    candidate = PolicyStore.from_text(candidate_yaml)
    assert candidate.get("pii_leakage").recommended_action == "block"

    result = compare_policy_versions([_pii_example()], _BASELINE, candidate, _FORBIDDEN, StubJudgeClient())
    assert result.total_examples == 1
    assert result.changed_count == 1
    diff = result.diffs[0]
    assert diff.label == "pii-email"
    assert diff.baseline_decision == "rewrite"
    assert diff.candidate_decision == "block"
    assert diff.added_policy_ids == []
    assert diff.removed_policy_ids == []


def test_removing_a_policy_drops_its_findings_in_the_candidate():
    data = yaml.safe_load(_POLICIES_YAML)
    data["policies"] = [p for p in data["policies"] if p["id"] != "pii_leakage"]
    candidate = PolicyStore.from_text(yaml.safe_dump(data))
    assert candidate.get("pii_leakage") is None

    result = compare_policy_versions([_pii_example()], _BASELINE, candidate, _FORBIDDEN, StubJudgeClient())
    diff = result.diffs[0]
    assert diff.baseline_decision == "rewrite"
    assert diff.candidate_decision == "approve"
    assert diff.removed_policy_ids == ["pii_leakage"]
    assert diff.added_policy_ids == []


def test_compare_does_not_pollute_a_real_audit_log():
    real_audit = AuditLog()
    real_engine = ReviewEngine(_BASELINE, _FORBIDDEN, PolicyJudge(_BASELINE, StubJudgeClient()), real_audit)
    real_engine.review(ReviewRequest(prompt="What's the weather?", output="Sunny.", feature="weather-bot"))
    assert len(real_audit.all()) == 1

    compare_policy_versions([_pii_example()], _BASELINE, _BASELINE, _FORBIDDEN, StubJudgeClient())
    assert len(real_audit.all()) == 1
