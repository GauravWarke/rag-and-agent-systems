from app.quality.judge import score_similarity


def test_identical_text_scores_one():
    assert score_similarity("hello world", "hello world") == 1.0


def test_completely_different_text_scores_zero():
    assert score_similarity("apples oranges bananas", "quantum flux capacitor") == 0.0


def test_partial_overlap_scores_between_zero_and_one():
    score = score_similarity("the quick brown fox", "the quick brown dog")
    assert 0.0 < score < 1.0


def test_both_empty_scores_one():
    assert score_similarity("", "") == 1.0


def test_one_empty_scores_zero():
    assert score_similarity("hello", "") == 0.0


def test_case_and_punctuation_insensitive():
    assert score_similarity("Hello, World!", "hello world") == 1.0
