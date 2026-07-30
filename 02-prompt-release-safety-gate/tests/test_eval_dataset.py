from app.eval.dataset import load_golden_set


def test_load_golden_set_returns_all_cases():
    cases = load_golden_set()
    assert len(cases) >= 75


def test_golden_set_ids_are_unique_and_stable():
    cases = load_golden_set()
    ids = [c.id for c in cases]
    assert len(ids) == len(set(ids))
    assert ids[0] == "c001"


def test_golden_set_covers_expected_categories():
    cases = load_golden_set()
    categories = {c.category for c in cases}
    for expected_category in (
        "spelling_mistakes",
        "vague_request",
        "emotional_customer",
        "missing_context",
        "mixed_intent",
        "safety_sensitive",
        "pii_present",
    ):
        assert expected_category in categories


def test_golden_case_has_required_labels():
    cases = load_golden_set()
    for case in cases:
        assert case.difficulty in {"easy", "medium", "hard"}
        assert case.why_this_case_exists
        assert case.expected.sentiment
        assert case.expected.urgency
