"""Deduplicate proposed eval candidates against the growing eval dataset.

A candidate whose prompt is nearly identical (by cosine similarity of
its embedding) to an already-accepted case is rejected as a duplicate
rather than bloating the dataset. Every candidate — accepted or
rejected — records why, so the acceptance/rejection trail stays
auditable.
"""
from __future__ import annotations

import uuid

import numpy as np

from app.core.config import settings
from app.core.models import EvalCandidate, LogEntry, ProposedLabel
from app.sampling.embeddings import cosine, embed


class EvalCandidateStore:
    def __init__(self) -> None:
        self._candidates: list[EvalCandidate] = []
        self._vectors: dict[str, np.ndarray] = {}

    def accepted(self) -> list[EvalCandidate]:
        return [c for c in self._candidates if c.status == "accepted"]

    def all(self) -> list[EvalCandidate]:
        return list(self._candidates)

    def get(self, candidate_id: str) -> EvalCandidate | None:
        return next((c for c in self._candidates if c.id == candidate_id), None)

    def update(self, candidate: EvalCandidate) -> None:
        """Replace a stored candidate in place, keyed by id. The vector map
        is untouched since edits only ever change label fields, not the
        source prompt the vector was computed from."""
        for i, existing in enumerate(self._candidates):
            if existing.id == candidate.id:
                self._candidates[i] = candidate
                return
        raise KeyError(f"No candidate with id '{candidate.id}'")

    def record(self, candidate: EvalCandidate, vector: np.ndarray | None) -> None:
        self._candidates.append(candidate)
        if vector is not None:
            self._vectors[candidate.id] = vector

    def vector_for(self, candidate_id: str) -> np.ndarray | None:
        return self._vectors.get(candidate_id)

    def clear(self) -> None:
        self._candidates.clear()
        self._vectors.clear()


def dedupe_and_add(
    log: LogEntry,
    proposed: ProposedLabel,
    store: EvalCandidateStore,
    threshold: float | None = None,
) -> EvalCandidate:
    threshold = settings.dedupe_similarity_threshold if threshold is None else threshold
    vector = embed(log.prompt)

    best_match: EvalCandidate | None = None
    best_similarity = 0.0
    for existing in store.accepted():
        existing_vector = store.vector_for(existing.id)
        if existing_vector is None:
            continue
        similarity = cosine(vector, existing_vector)
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = existing

    candidate_id = str(uuid.uuid4())
    if best_match is not None and best_similarity >= threshold:
        candidate = EvalCandidate(
            id=candidate_id,
            log_id=log.id,
            feature=log.feature,
            input=log.prompt,
            eval_type=proposed.eval_type,
            expected_behavior=proposed.expected_behavior,
            key_assertions=proposed.key_assertions,
            forbidden_assertions=proposed.forbidden_assertions,
            rubric=proposed.rubric,
            confidence=proposed.confidence,
            status="rejected_duplicate",
            reason=f"near-duplicate of case {best_match.id} (similarity {best_similarity:.3f} >= {threshold})",
            duplicate_of=best_match.id,
            review_status="rejected",
        )
        store.record(candidate, None)
        return candidate

    review_status = (
        "approved" if proposed.confidence >= settings.review_confidence_threshold else "draft"
    )
    candidate = EvalCandidate(
        id=candidate_id,
        log_id=log.id,
        feature=log.feature,
        input=log.prompt,
        eval_type=proposed.eval_type,
        expected_behavior=proposed.expected_behavior,
        key_assertions=proposed.key_assertions,
        forbidden_assertions=proposed.forbidden_assertions,
        rubric=proposed.rubric,
        confidence=proposed.confidence,
        status="accepted",
        reason="accepted: no existing case above the similarity threshold",
        duplicate_of=None,
        review_status=review_status,
    )
    store.record(candidate, vector)
    return candidate
