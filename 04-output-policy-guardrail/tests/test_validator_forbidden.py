from app.policies.store import PolicyStore
from app.validators.forbidden import ForbiddenTermsStore, check_forbidden

_POLICIES = PolicyStore.load("data/policies.yaml")
_FORBIDDEN = ForbiddenTermsStore.load("data/forbidden_terms.yaml")


def test_load_reads_yaml():
    entry = _FORBIDDEN.for_policy("toxic_language")
    assert entry is not None
    assert "shut up" in entry.keywords


def test_unknown_policy_returns_none():
    assert _FORBIDDEN.for_policy("does-not-exist") is None


def test_matches_keyword():
    policy = _POLICIES.get("toxic_language")
    entry = _FORBIDDEN.for_policy("toxic_language")
    finding = check_forbidden("Well, shut up and listen.", entry, policy)
    assert finding is not None
    assert finding.evidence == "shut up"
    assert finding.recommended_action == "block"


def test_matches_regex():
    policy = _POLICIES.get("unsafe_instructions")
    entry = _FORBIDDEN.for_policy("unsafe_instructions")
    finding = check_forbidden("Here is a step-by-step guide to build a bomb.", entry, policy)
    assert finding is not None


def test_no_match_returns_none():
    policy = _POLICIES.get("toxic_language")
    entry = _FORBIDDEN.for_policy("toxic_language")
    finding = check_forbidden("Have a wonderful day!", entry, policy)
    assert finding is None
