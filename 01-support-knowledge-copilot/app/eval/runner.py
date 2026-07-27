"""Eval runner (Phase 5, step 2/4): runs the golden Q&A set through the
retrieval + generation pipeline for a given strategy and scores the result.

Builds its own `HybridRetriever` over the bundled sample corpus rather than
reusing `app.main`'s module-level instance, so a run is self-contained and
safe to call repeatedly (e.g. once per strategy) without app lifespan setup.
"""
from __future__ import annotations

from app.eval.golden import GoldenQA, load_golden_set
from app.eval.metrics import CaseResult, EvalSummary, evaluate_case, summarize
from app.generation.answer import generate
from app.ingestion.loader import load_sample_corpus
from app.retrieval.hybrid import HybridRetriever


def run_eval(strategy: str = "hybrid", cases: list[GoldenQA] | None = None) -> EvalSummary:
    """Run every golden case through retrieval + generation and score it."""
    cases = load_golden_set() if cases is None else cases

    retriever = HybridRetriever()
    retriever.index(load_sample_corpus())

    results: list[CaseResult] = []
    for case in cases:
        retrieved = retriever.retrieve(case.question, strategy=strategy)
        response = generate(case.question, retrieved)
        results.append(evaluate_case(case, response, strategy))

    return summarize(strategy, results)
