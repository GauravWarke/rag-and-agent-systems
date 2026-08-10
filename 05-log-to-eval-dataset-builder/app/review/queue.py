"""Human review queue: which auto-generated candidates still need a human
look, and what already-approved cases they most resemble.

Only "accepted" (non-duplicate) candidates with `review_status == "draft"`
are queued — those are exactly the low-confidence proposals from
`app.labels.generator` that `dedupe_and_add` didn't auto-approve.
"""
from __future__ import annotations

from app.core.models import EvalCandidate, ReviewQueueItem
from app.labels.dedupe import EvalCandidateStore
from app.logs.store import LogStore
from app.sampling.embeddings import cosine, embed


def pending_review(store: EvalCandidateStore) -> list[EvalCandidate]:
    return [c for c in store.all() if c.status == "accepted" and c.review_status == "draft"]


def similar_cases(candidate: EvalCandidate, store: EvalCandidateStore, top_n: int = 3) -> list[EvalCandidate]:
    """Already-approved cases whose input prompt is closest to this
    candidate's, so a reviewer can check for near-duplicate or
    inconsistent labeling before deciding."""
    vector = store.vector_for(candidate.id)
    if vector is None:
        vector = embed(candidate.input)

    scored: list[tuple[float, EvalCandidate]] = []
    for other in store.all():
        if other.id == candidate.id or other.review_status != "approved":
            continue
        other_vector = store.vector_for(other.id)
        if other_vector is None:
            continue
        scored.append((cosine(vector, other_vector), other))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [c for _score, c in scored[:top_n]]


def build_queue_item(candidate: EvalCandidate, log_store: LogStore, candidate_store: EvalCandidateStore) -> ReviewQueueItem | None:
    log = log_store.get(candidate.log_id)
    if log is None:
        return None
    return ReviewQueueItem(candidate=candidate, log=log, similar_cases=similar_cases(candidate, candidate_store))


def build_queue(candidate_store: EvalCandidateStore, log_store: LogStore) -> list[ReviewQueueItem]:
    items = (build_queue_item(c, log_store, candidate_store) for c in pending_review(candidate_store))
    return [item for item in items if item is not None]
