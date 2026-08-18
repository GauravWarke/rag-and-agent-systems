from pathlib import Path

from app.answers.generator import StubAnswerGenerator, generate_answers
from app.core.models import ChunkRecord, ProbeQuestion
from app.drift.probes import load_probes
from app.indexing.chunker import build_chunks

_CHUNKS = [
    ChunkRecord(
        chunk_id="policies::refund-policy",
        doc_source="policies.md",
        doc_type="policy",
        section_heading="Refund Policy",
        text="Customers can request a refund within 30 days. Approved refunds are processed within 5 business days.",
        chunk_hash="h1",
        last_modified="2025-01-01",
        embedding_version="stub-v1",
    ),
]


def test_stub_generator_cites_chunk_and_uses_first_sentence():
    generator = StubAnswerGenerator()
    answer = generator.generate("How many days for a refund?", _CHUNKS[0])
    assert answer == "Customers can request a refund within 30 days. [source: policies::refund-policy]"


def test_stub_generator_handles_no_match():
    generator = StubAnswerGenerator()
    assert generator.generate("anything", None) == "I could not find this in the docs."


def test_generate_answers_grounds_each_probe_in_a_chunk():
    probes = [ProbeQuestion(probe_id="p1", question="How many days for a refund?", expected_chunk_id="policies::refund-policy")]
    summary = generate_answers(probes, _CHUNKS)
    assert len(summary.answers) == 1
    assert summary.answers[0].chunk_id == "policies::refund-policy"
    assert "[source: policies::refund-policy]" in summary.answers[0].answer_text


def test_generate_answers_over_bundled_corpus_covers_every_probe():
    repo_root = Path(__file__).resolve().parents[1]
    chunks = build_chunks(repo_root / "data" / "docs", repo_root / "data" / "docs_meta.json", "stub-v1")
    probes = load_probes(repo_root / "data" / "probes.json")

    summary = generate_answers(probes, chunks)

    assert len(summary.answers) == len(probes)
    assert all(a.answer_text for a in summary.answers)
