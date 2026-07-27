from app.eval.golden import GoldenCategory, load_golden_set


def test_golden_set_loads_and_has_reasonable_coverage():
    cases = load_golden_set()
    assert len(cases) >= 30


def test_golden_set_ids_are_unique():
    cases = load_golden_set()
    ids = [c.id for c in cases]
    assert len(ids) == len(set(ids))


def test_golden_set_covers_every_category():
    cases = load_golden_set()
    seen = {c.category for c in cases}
    assert seen == set(GoldenCategory)


def test_no_answer_cases_flag_expect_no_answer():
    cases = load_golden_set()
    no_answer_cases = [c for c in cases if c.category == GoldenCategory.no_answer]
    assert no_answer_cases
    assert all(c.expect_no_answer for c in no_answer_cases)
