"""Compare two probe-answer runs to detect answer drift, and cross-
reference against a freshness diff to flag stale-answer risk: source
sections that changed but whose generated answers did not.

Retrieval drift (Phase 3) tells us *which chunk* a probe returns
changed. Answer drift asks the follow-up question: did the answer text
itself change in meaning? A source section can change while the cached
or regenerated answer stays word-for-word the same — that's the stale
knowledge case this module flags.
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.answers.judge import AnswerJudgeClient, StubAnswerJudgeClient
from app.core.models import (
    AnswerDriftReport,
    AnswerDriftVerdict,
    AnswerRunSummary,
    ChunkRecord,
    FreshnessDiff,
    StaleAnswerReport,
    StaleAnswerRisk,
)


def compare_answer_runs(
    previous: AnswerRunSummary,
    current: AnswerRunSummary,
    chunks: list[ChunkRecord],
    judge: AnswerJudgeClient | None = None,
) -> AnswerDriftReport:
    judge = judge or StubAnswerJudgeClient()
    chunks_by_id = {c.chunk_id: c for c in chunks}
    previous_by_id = {a.probe_id: a for a in previous.answers}

    verdicts: list[AnswerDriftVerdict] = []
    for current_answer in current.answers:
        prior = previous_by_id.get(current_answer.probe_id)
        if prior is None:
            continue
        current_chunk = chunks_by_id.get(current_answer.chunk_id) if current_answer.chunk_id else None
        verdict = judge.compare(
            current_answer.question,
            prior.answer_text,
            current_answer.answer_text,
            current_chunk,
        )
        verdicts.append(
            AnswerDriftVerdict(
                probe_id=current_answer.probe_id,
                question=current_answer.question,
                chunk_id=current_answer.chunk_id,
                previous_answer=prior.answer_text,
                current_answer=current_answer.answer_text,
                meaning_changed=verdict.meaning_changed,
                citation_supports_answer=verdict.citation_supports_answer,
                rationale=verdict.rationale,
            )
        )
    return AnswerDriftReport(
        previous_run_at=previous.run_at,
        current_run_at=current.run_at,
        verdicts=verdicts,
    )


def detect_stale_answer_risk(diff: FreshnessDiff, drift: AnswerDriftReport) -> StaleAnswerReport:
    """A probe is at stale-answer risk when the chunk it's grounded in
    changed (added/removed/modified in the freshness diff) but the
    generated answer for that probe did not change in meaning."""
    changed_chunk_ids = {c.chunk_id for c in (*diff.added, *diff.removed, *diff.modified)}
    risks = [
        StaleAnswerRisk(
            probe_id=v.probe_id,
            question=v.question,
            chunk_id=v.chunk_id,
            reason=(
                f"Source chunk '{v.chunk_id}' changed since the last index, but the "
                "generated answer for this probe did not — it may be serving stale knowledge."
            ),
        )
        for v in drift.verdicts
        if v.chunk_id in changed_chunk_ids and not v.meaning_changed
    ]
    return StaleAnswerReport(checked_at=datetime.now(UTC).isoformat(), risks=risks)
