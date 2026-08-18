import pytest

from app.answers.judge import StubAnswerJudgeClient
from app.core.models import ChunkRecord

_CHUNK = ChunkRecord(
    chunk_id="policies::refund-policy",
    doc_source="policies.md",
    doc_type="policy",
    section_heading="Refund Policy",
    text="Customers can request a refund within 30 days.",
    chunk_hash="h1",
    last_modified="2025-01-01",
    embedding_version="stub-v1",
)


def test_identical_answers_have_no_meaning_change():
    judge = StubAnswerJudgeClient()
    answer = "Customers can request a refund within 30 days. [source: policies::refund-policy]"
    verdict = judge.compare("How many days for a refund?", answer, answer, _CHUNK)
    assert verdict.meaning_changed is False
    assert verdict.citation_supports_answer is True


def test_substantially_different_answers_flag_meaning_change():
    judge = StubAnswerJudgeClient()
    previous = "Customers can request a refund within 30 days. [source: policies::refund-policy]"
    current = "Refunds are no longer offered under any circumstances. [source: policies::refund-policy]"
    verdict = judge.compare("How many days for a refund?", previous, current, _CHUNK)
    assert verdict.meaning_changed is True


def test_missing_citation_is_flagged_as_unsupported():
    judge = StubAnswerJudgeClient()
    verdict = judge.compare("q", "a", "a totally different answer with no citation", None)
    assert verdict.citation_supports_answer is False


def test_openai_judge_requires_api_key():
    from app.answers.judge import OpenAIAnswerJudgeClient

    judge = OpenAIAnswerJudgeClient(api_key="")
    with pytest.raises(RuntimeError):
        judge.compare("q", "a", "b", None)
