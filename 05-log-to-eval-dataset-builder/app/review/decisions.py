"""Apply human review decisions to eval candidates: approve as-is, edit
label fields and approve, or reject. Every decision is written to an
append-only edit log with the diff and the reviewer's stated reason, so
auto-label quality can be measured later from what humans actually changed.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from app.core.models import (
    DeprecateRequest,
    EvalCandidate,
    FieldChange,
    ReviewDecisionRequest,
    ReviewDecisionResponse,
    ReviewEditLogEntry,
)
from app.labels.dedupe import EvalCandidateStore

_EDITABLE_FIELDS = ("eval_type", "expected_behavior", "key_assertions", "forbidden_assertions", "rubric")


class ReviewEditLogStore:
    def __init__(self) -> None:
        self._entries: list[ReviewEditLogEntry] = []

    def add(self, entry: ReviewEditLogEntry) -> None:
        self._entries.append(entry)

    def all(self) -> list[ReviewEditLogEntry]:
        return list(self._entries)

    def for_candidate(self, candidate_id: str) -> list[ReviewEditLogEntry]:
        return [e for e in self._entries if e.candidate_id == candidate_id]

    def clear(self) -> None:
        self._entries.clear()


def _field_diff(candidate: EvalCandidate, edits) -> tuple[EvalCandidate, list[FieldChange]]:
    changes: list[FieldChange] = []
    updates = {}
    for field in _EDITABLE_FIELDS:
        new_value = getattr(edits, field)
        if new_value is None:
            continue
        old_value = getattr(candidate, field)
        if new_value == old_value:
            continue
        changes.append(
            FieldChange(field=field, old_value=str(old_value), new_value=str(new_value))
        )
        updates[field] = new_value
    updated = candidate.model_copy(update=updates) if updates else candidate
    return updated, changes


def apply_decision(
    req: ReviewDecisionRequest,
    candidate_store: EvalCandidateStore,
    edit_log_store: ReviewEditLogStore,
    now: datetime,
) -> ReviewDecisionResponse:
    candidate = candidate_store.get(req.candidate_id)
    if candidate is None:
        raise KeyError(f"No eval candidate with id '{req.candidate_id}'")
    if candidate.status != "accepted":
        raise ValueError(f"Candidate '{req.candidate_id}' was never accepted into the dataset and cannot be reviewed.")

    changes: list[FieldChange] = []
    updated = candidate

    if req.action == "approve":
        updated = candidate.model_copy(update={"review_status": "approved"})
    elif req.action == "reject":
        updated = candidate.model_copy(update={"review_status": "rejected"})
    elif req.action == "edit":
        if req.edits is None:
            raise ValueError("action 'edit' requires an 'edits' payload.")
        updated, changes = _field_diff(candidate, req.edits)
        updated = updated.model_copy(update={"review_status": "approved"})
    else:
        raise ValueError(f"Unsupported review action '{req.action}'; use approve, edit, or reject.")

    candidate_store.update(updated)

    log_entry = ReviewEditLogEntry(
        id=str(uuid.uuid4()),
        candidate_id=req.candidate_id,
        reviewer=req.reviewer,
        action=req.action,
        reason=req.reason,
        changed_fields=changes,
        timestamp=now,
    )
    edit_log_store.add(log_entry)
    return ReviewDecisionResponse(candidate=updated, edit_log=log_entry)


def deprecate_candidate(
    req: DeprecateRequest,
    candidate_store: EvalCandidateStore,
    edit_log_store: ReviewEditLogStore,
    now: datetime,
) -> ReviewDecisionResponse:
    candidate = candidate_store.get(req.candidate_id)
    if candidate is None:
        raise KeyError(f"No eval candidate with id '{req.candidate_id}'")
    if candidate.review_status != "approved":
        raise ValueError(f"Only approved cases can be deprecated; '{req.candidate_id}' is '{candidate.review_status}'.")

    updated = candidate.model_copy(update={"review_status": "deprecated"})
    candidate_store.update(updated)

    log_entry = ReviewEditLogEntry(
        id=str(uuid.uuid4()),
        candidate_id=req.candidate_id,
        reviewer=req.reviewer,
        action="reject",
        reason=req.reason,
        changed_fields=[FieldChange(field="review_status", old_value="approved", new_value="deprecated")],
        timestamp=now,
    )
    edit_log_store.add(log_entry)
    return ReviewDecisionResponse(candidate=updated, edit_log=log_entry)
