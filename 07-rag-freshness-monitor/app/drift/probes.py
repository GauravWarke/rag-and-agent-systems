"""Run the recurring probe question set against a chunk snapshot and detect
retrieval drift by comparing consecutive runs.

Each probe is a question tied to the chunk ID it's expected to retrieve.
Running the same probes before and after a document update tells us
whether the update changed which section answers a known question —
that's retrieval drift, independent of whether the *answer text* itself
changed.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.core.models import (
    ChunkRecord,
    DriftedProbe,
    DriftReport,
    ProbeQuestion,
    ProbeResult,
    ProbeRunSummary,
)
from app.drift.retriever import top_match


def load_probes(probes_path: Path) -> list[ProbeQuestion]:
    raw = json.loads(probes_path.read_text(encoding="utf-8"))
    return [ProbeQuestion.model_validate(item) for item in raw]


def run_probes(probes: list[ProbeQuestion], chunks: list[ChunkRecord]) -> ProbeRunSummary:
    results: list[ProbeResult] = []
    for probe in probes:
        chunk_id, score = top_match(probe.question, chunks)
        results.append(
            ProbeResult(
                probe_id=probe.probe_id,
                question=probe.question,
                expected_chunk_id=probe.expected_chunk_id,
                retrieved_chunk_id=chunk_id,
                retrieval_score=score,
                matched_expected=chunk_id == probe.expected_chunk_id,
            )
        )
    matched = sum(1 for r in results if r.matched_expected)
    return ProbeRunSummary(
        run_at=datetime.now(UTC).isoformat(),
        total_probes=len(results),
        matched=matched,
        match_rate=matched / len(results) if results else 0.0,
        results=results,
    )


def compare_runs(previous: ProbeRunSummary, current: ProbeRunSummary) -> DriftReport:
    """Flag probes whose top retrieved chunk changed between two runs, or
    that no longer retrieve their expected chunk."""
    previous_by_id = {r.probe_id: r for r in previous.results}
    drifted: list[DriftedProbe] = []
    for current_result in current.results:
        prior = previous_by_id.get(current_result.probe_id)
        if prior is None:
            continue
        top_changed = prior.retrieved_chunk_id != current_result.retrieved_chunk_id
        newly_wrong = prior.matched_expected and not current_result.matched_expected
        if top_changed or newly_wrong:
            drifted.append(
                DriftedProbe(
                    probe_id=current_result.probe_id,
                    question=current_result.question,
                    previous_chunk_id=prior.retrieved_chunk_id,
                    current_chunk_id=current_result.retrieved_chunk_id,
                    expected_chunk_id=current_result.expected_chunk_id,
                    now_matches_expected=current_result.matched_expected,
                )
            )
    return DriftReport(
        previous_run_at=previous.run_at,
        current_run_at=current.run_at,
        drifted=drifted,
    )
