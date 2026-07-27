from app.core.models import Citation
from app.generation import confidence


def _citation(supported):
    return Citation(chunk_id="c1", claim="x", supported=supported, evidence_span="x")


def test_citation_support_rate_empty_is_zero():
    assert confidence.citation_support_rate([]) == 0.0


def test_citation_support_rate_mixed():
    citations = [_citation(True), _citation(True), _citation(False)]
    assert confidence.citation_support_rate(citations) == 2 / 3


def test_answer_completeness_caps_at_one():
    assert confidence.answer_completeness(retrieved_count=10, target_count=5) == 1.0
    assert confidence.answer_completeness(retrieved_count=2, target_count=5) == 0.4


def test_score_combines_signals_into_breakdown():
    citations = [_citation(True), _citation(False)]
    breakdown = confidence.score(top_score=0.8, citations=citations, retrieved_count=5, target_count=5)
    assert breakdown.retrieval_score == 0.8
    assert breakdown.citation_support_rate == 0.5
    assert breakdown.answer_completeness == 1.0
    assert breakdown.no_answer_detected is False
    expected = round(0.5 * 0.8 + 0.3 * 0.5 + 0.2 * 1.0, 4)
    assert breakdown.final == expected
