import json
from pathlib import Path

from app.core.models import ChunkRecord, ProbeQuestion
from app.drift.probes import compare_runs, load_probes, run_probes
from app.drift.retriever import top_match
from app.indexing.chunker import build_chunks

_CHUNKS = [
    ChunkRecord(
        chunk_id="policies::refund-policy",
        doc_source="policies.md",
        doc_type="policy",
        section_heading="Refund Policy",
        text="Customers can request a refund within 30 days if the product has not been activated.",
        chunk_hash="h1",
        last_modified="2025-01-01",
        embedding_version="stub-v1",
    ),
    ChunkRecord(
        chunk_id="troubleshooting::sync-errors",
        doc_source="troubleshooting.md",
        doc_type="troubleshooting",
        section_heading="Sync Errors",
        text="Sync errors are usually caused by an expired OAuth token that needs reconnecting.",
        chunk_hash="h2",
        last_modified="2025-01-01",
        embedding_version="stub-v1",
    ),
]


def test_top_match_returns_none_for_empty_chunk_set():
    chunk_id, score = top_match("anything", [])
    assert chunk_id is None
    assert score == 0.0


def test_top_match_prefers_lexically_closer_chunk():
    chunk_id, score = top_match("Why do I keep getting sync errors with my OAuth token?", _CHUNKS)
    assert chunk_id == "troubleshooting::sync-errors"
    assert score > 0.0


def test_load_probes_parses_json(tmp_path: Path):
    path = tmp_path / "probes.json"
    path.write_text(json.dumps([{"probe_id": "p1", "question": "q?", "expected_chunk_id": "a::b"}]), encoding="utf-8")
    probes = load_probes(path)
    assert probes == [ProbeQuestion(probe_id="p1", question="q?", expected_chunk_id="a::b")]


def test_run_probes_computes_match_rate():
    probes = [
        ProbeQuestion(probe_id="p1", question="How many days for a refund?", expected_chunk_id="policies::refund-policy"),
        ProbeQuestion(probe_id="p2", question="Why do sync errors happen with OAuth?", expected_chunk_id="troubleshooting::sync-errors"),
    ]
    summary = run_probes(probes, _CHUNKS)
    assert summary.total_probes == 2
    assert summary.matched == 2
    assert summary.match_rate == 1.0


def test_compare_runs_flags_top_result_change():
    probes = [ProbeQuestion(probe_id="p1", question="refund days", expected_chunk_id="policies::refund-policy")]
    before = run_probes(probes, _CHUNKS)
    # Remove the expected chunk so the top match must change.
    after_chunks = [c for c in _CHUNKS if c.chunk_id != "policies::refund-policy"]
    after = run_probes(probes, after_chunks)

    drift = compare_runs(before, after)

    assert drift.drift_count == 1
    assert drift.drifted[0].probe_id == "p1"
    assert drift.drifted[0].now_matches_expected is False


def test_compare_runs_no_drift_when_nothing_changes():
    probes = [ProbeQuestion(probe_id="p1", question="refund days", expected_chunk_id="policies::refund-policy")]
    before = run_probes(probes, _CHUNKS)
    after = run_probes(probes, _CHUNKS)

    drift = compare_runs(before, after)

    assert drift.drift_count == 0


def test_bundled_probe_set_has_reasonable_match_rate():
    repo_root = Path(__file__).resolve().parents[1]
    chunks = build_chunks(repo_root / "data" / "docs", repo_root / "data" / "docs_meta.json", "stub-v1")
    probes = load_probes(repo_root / "data" / "probes.json")

    summary = run_probes(probes, chunks)

    assert summary.total_probes == len(probes)
    # The stub embedder is a crude offline bag-of-words hash, not a real
    # semantic model — we only require it to beat random chance (1/16).
    assert summary.match_rate > 0.5
