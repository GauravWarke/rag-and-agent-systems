from app.answers.drift import compare_answer_runs, detect_stale_answer_risk
from app.core.models import (
    AnswerRecord,
    AnswerRunSummary,
    ChunkRecord,
    FreshnessDiff,
    SectionChange,
)

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


def _run(run_at: str, answer_text: str) -> AnswerRunSummary:
    return AnswerRunSummary(
        run_at=run_at,
        answers=[
            AnswerRecord(
                probe_id="p1",
                question="How many days for a refund?",
                chunk_id="policies::refund-policy",
                answer_text=answer_text,
            )
        ],
    )


def test_compare_answer_runs_flags_meaning_change():
    previous = _run("t0", "Customers can request a refund within 30 days. [source: policies::refund-policy]")
    current = _run("t1", "Refunds are no longer offered under any circumstances. [source: policies::refund-policy]")

    drift = compare_answer_runs(previous, current, [_CHUNK])

    assert drift.previous_run_at == "t0"
    assert drift.current_run_at == "t1"
    assert drift.changed_count == 1
    assert drift.verdicts[0].meaning_changed is True


def test_compare_answer_runs_no_drift_when_answer_is_unchanged():
    same_text = "Customers can request a refund within 30 days. [source: policies::refund-policy]"
    previous = _run("t0", same_text)
    current = _run("t1", same_text)

    drift = compare_answer_runs(previous, current, [_CHUNK])

    assert drift.changed_count == 0


def test_compare_answer_runs_skips_probes_missing_from_previous_run():
    previous = AnswerRunSummary(run_at="t0", answers=[])
    current = _run("t1", "some answer")

    drift = compare_answer_runs(previous, current, [_CHUNK])

    assert drift.verdicts == []


def test_detect_stale_answer_risk_flags_unchanged_answer_for_changed_chunk():
    diff = FreshnessDiff(
        manifest_created_at="t0",
        scanned_at="t1",
        modified=[
            SectionChange(
                chunk_id="policies::refund-policy",
                doc_source="policies.md",
                section_heading="Refund Policy",
                change_type="modified",
                old_text="old",
                new_text="new",
                semantic_change_score=0.5,
            )
        ],
    )
    same_text = "Customers can request a refund within 30 days. [source: policies::refund-policy]"
    drift = compare_answer_runs(_run("t0", same_text), _run("t1", same_text), [_CHUNK])

    report = detect_stale_answer_risk(diff, drift)

    assert report.at_risk_count == 1
    assert report.risks[0].probe_id == "p1"
    assert report.risks[0].chunk_id == "policies::refund-policy"


def test_detect_stale_answer_risk_ignores_changed_chunks_with_changed_answers():
    diff = FreshnessDiff(
        manifest_created_at="t0",
        scanned_at="t1",
        modified=[
            SectionChange(
                chunk_id="policies::refund-policy",
                doc_source="policies.md",
                section_heading="Refund Policy",
                change_type="modified",
                old_text="old",
                new_text="new",
                semantic_change_score=0.5,
            )
        ],
    )
    previous = _run("t0", "Customers can request a refund within 30 days. [source: policies::refund-policy]")
    current = _run("t1", "Refunds are no longer offered under any circumstances. [source: policies::refund-policy]")
    drift = compare_answer_runs(previous, current, [_CHUNK])

    report = detect_stale_answer_risk(diff, drift)

    assert report.at_risk_count == 0


def test_detect_stale_answer_risk_ignores_unchanged_chunks():
    diff = FreshnessDiff(manifest_created_at="t0", scanned_at="t1")
    same_text = "Customers can request a refund within 30 days. [source: policies::refund-policy]"
    drift = compare_answer_runs(_run("t0", same_text), _run("t1", same_text), [_CHUNK])

    report = detect_stale_answer_risk(diff, drift)

    assert report.at_risk_count == 0
