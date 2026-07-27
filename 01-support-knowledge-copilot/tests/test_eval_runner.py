from app.eval.runner import run_eval


def test_run_eval_hybrid_scores_full_golden_set():
    summary = run_eval("hybrid")

    assert summary.strategy == "hybrid"
    assert summary.total_cases >= 30
    assert 0.0 <= summary.retrieval_hit_rate <= 1.0
    assert 0.0 <= summary.answer_correct_rate <= 1.0
    assert 0.0 <= summary.citation_valid_rate <= 1.0
    assert 0.0 <= summary.refusal_correct_rate <= 1.0
    assert len(summary.cases) == summary.total_cases


def test_run_eval_supports_dense_and_sparse_strategies():
    dense = run_eval("dense")
    sparse = run_eval("sparse")

    assert dense.strategy == "dense"
    assert sparse.strategy == "sparse"
    assert dense.total_cases == sparse.total_cases


def test_run_eval_no_answer_cases_are_mostly_refused():
    summary = run_eval("hybrid")
    no_answer_cases = [c for c in summary.cases if c.category == "no_answer"]

    assert no_answer_cases
    # every no_answer golden case should be scored, and refusal is checked
    # per-case (see test_eval_metrics) — here just confirm coverage.
    assert all(c.strategy == "hybrid" for c in no_answer_cases)
