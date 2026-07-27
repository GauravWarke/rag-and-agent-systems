from app.core.models import (
    AskResponse,
    Chunk,
    ChunkMetadata,
    Citation,
    ConfidenceBreakdown,
    DocType,
    RetrievedChunk,
)
from app.eval.golden import GoldenCategory, GoldenQA
from app.eval.metrics import evaluate_case, summarize


def _chunk(source_name: str, text: str = "some text") -> RetrievedChunk:
    return RetrievedChunk(
        chunk=Chunk(chunk_id=f"{source_name}-1", text=text,
                    metadata=ChunkMetadata(source_name=source_name, doc_type=DocType.faq)),
        fused_score=0.9,
    )


def _case(**overrides) -> GoldenQA:
    defaults = {"id": "q1", "question": "q", "category": GoldenCategory.simple_lookup}
    defaults.update(overrides)
    return GoldenQA(**defaults)


def test_retrieval_correct_when_expected_source_present():
    case = _case(expected_sources=["faq"])
    response = AskResponse(answer="a", confidence=ConfidenceBreakdown(), retrieved=[_chunk("faq")])

    result = evaluate_case(case, response, "hybrid")

    assert result.retrieval_applicable is True
    assert result.retrieval_correct is True


def test_retrieval_incorrect_when_expected_source_missing():
    case = _case(expected_sources=["api"])
    response = AskResponse(answer="a", confidence=ConfidenceBreakdown(), retrieved=[_chunk("faq")])

    result = evaluate_case(case, response, "hybrid")

    assert result.retrieval_correct is False


def test_retrieval_not_applicable_without_expectation():
    case = _case(expected_sources=[])
    response = AskResponse(answer="a", confidence=ConfidenceBreakdown(), retrieved=[_chunk("faq")])

    result = evaluate_case(case, response, "hybrid")

    assert result.retrieval_applicable is False


def test_answer_correct_requires_all_substrings():
    case = _case(expected_answer_contains=["60 requests", "per minute"])
    response = AskResponse(answer="Limit is 60 requests per minute total.",
                            confidence=ConfidenceBreakdown(), retrieved=[])

    assert evaluate_case(case, response, "hybrid").answer_correct is True

    response_missing = AskResponse(answer="Limit is 60 requests.",
                                    confidence=ConfidenceBreakdown(), retrieved=[])
    assert evaluate_case(case, response_missing, "hybrid").answer_correct is False


def test_citation_validity_reflects_unsupported_citation():
    case = _case()
    bad_citation = Citation(chunk_id="c1", claim="x", supported=False)
    response = AskResponse(answer="a", citations=[bad_citation],
                            confidence=ConfidenceBreakdown(), retrieved=[])

    result = evaluate_case(case, response, "hybrid")

    assert result.citation_applicable is True
    assert result.citations_valid is False


def test_refusal_correct_for_no_answer_case():
    case = _case(category=GoldenCategory.no_answer, expect_no_answer=True)
    response = AskResponse(
        answer="I could not find this in the docs.",
        confidence=ConfidenceBreakdown(no_answer_detected=True),
        retrieved=[],
    )

    assert evaluate_case(case, response, "hybrid").refusal_correct is True


def test_refusal_incorrect_when_system_wrongly_refuses():
    case = _case(expect_no_answer=False)
    response = AskResponse(
        answer="I could not find this in the docs.",
        confidence=ConfidenceBreakdown(no_answer_detected=True),
        retrieved=[],
    )

    assert evaluate_case(case, response, "hybrid").refusal_correct is False


def test_summarize_computes_rates_only_over_applicable_cases():
    case_with_expectation = _case(id="q1", expected_sources=["faq"])
    case_without_expectation = _case(id="q2", category=GoldenCategory.ambiguous)

    hit = evaluate_case(
        case_with_expectation,
        AskResponse(answer="a", confidence=ConfidenceBreakdown(), retrieved=[_chunk("faq")]),
        "hybrid",
    )
    no_expectation = evaluate_case(
        case_without_expectation,
        AskResponse(answer="a", confidence=ConfidenceBreakdown(), retrieved=[_chunk("api")]),
        "hybrid",
    )

    summary = summarize("hybrid", [hit, no_expectation])

    assert summary.total_cases == 2
    assert summary.retrieval_hit_rate == 1.0  # only q1 is applicable, and it's correct
