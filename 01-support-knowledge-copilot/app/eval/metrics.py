"""Retrieval/answer quality scoring (Phase 5, step 2).

Scores each golden case on four *separate* signals, as called out in the
build guide, instead of collapsing everything into one pass/fail number:

- retrieval: was a chunk from an expected source actually retrieved?
- answer: does the generated answer contain the expected substrings?
- citations: is every citation the answer makes actually supported?
- refusal: did the system refuse exactly when it should have (and only then)?

Retrieval/answer/citation checks are only meaningful when the golden case
makes a claim about them (e.g. an ambiguous question has no
`expected_sources`), so each has an `*_applicable` flag and the aggregate
rates in `summarize` are computed only over applicable cases.
"""
from __future__ import annotations

from pydantic import BaseModel

from app.core.models import AskResponse
from app.eval.golden import GoldenQA


class CaseResult(BaseModel):
    id: str
    question: str
    category: str
    strategy: str
    answer: str
    confidence: float
    retrieved_sources: list[str]
    retrieval_applicable: bool
    retrieval_correct: bool
    answer_applicable: bool
    answer_correct: bool
    citation_applicable: bool
    citations_valid: bool
    refusal_correct: bool


class EvalSummary(BaseModel):
    strategy: str
    total_cases: int
    retrieval_hit_rate: float
    answer_correct_rate: float
    citation_valid_rate: float
    refusal_correct_rate: float
    cases: list[CaseResult]


def _retrieval_correct(case: GoldenQA, retrieved_sources: list[str]) -> bool:
    return any(source in retrieved_sources for source in case.expected_sources)


def _answer_correct(case: GoldenQA, answer: str) -> bool:
    lower = answer.lower()
    return all(sub.lower() in lower for sub in case.expected_answer_contains)


def evaluate_case(case: GoldenQA, response: AskResponse, strategy: str) -> CaseResult:
    """Score one `AskResponse` against its golden case for the given strategy."""
    retrieved_sources = [r.chunk.metadata.source_name for r in response.retrieved]
    refused = response.confidence.no_answer_detected

    return CaseResult(
        id=case.id,
        question=case.question,
        category=case.category.value,
        strategy=strategy,
        answer=response.answer,
        confidence=response.confidence.final,
        retrieved_sources=retrieved_sources,
        retrieval_applicable=bool(case.expected_sources),
        retrieval_correct=_retrieval_correct(case, retrieved_sources),
        answer_applicable=bool(case.expected_answer_contains),
        answer_correct=_answer_correct(case, response.answer),
        citation_applicable=bool(response.citations),
        citations_valid=all(c.supported for c in response.citations) if response.citations else False,
        refusal_correct=refused == case.expect_no_answer,
    )


def _rate(cases: list[CaseResult], applicable_attr: str, correct_attr: str) -> float:
    applicable = [c for c in cases if getattr(c, applicable_attr)]
    if not applicable:
        return 0.0
    return sum(1 for c in applicable if getattr(c, correct_attr)) / len(applicable)


def summarize(strategy: str, cases: list[CaseResult]) -> EvalSummary:
    """Aggregate per-case results into strategy-level rates."""
    refusal_rate = sum(1 for c in cases if c.refusal_correct) / len(cases) if cases else 0.0
    return EvalSummary(
        strategy=strategy,
        total_cases=len(cases),
        retrieval_hit_rate=round(_rate(cases, "retrieval_applicable", "retrieval_correct"), 4),
        answer_correct_rate=round(_rate(cases, "answer_applicable", "answer_correct"), 4),
        citation_valid_rate=round(_rate(cases, "citation_applicable", "citations_valid"), 4),
        refusal_correct_rate=round(refusal_rate, 4),
        cases=cases,
    )
