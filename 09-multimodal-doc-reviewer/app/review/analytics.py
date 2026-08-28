"""Review-queue analytics (Phase 5, step 3).

`average_review_time_seconds` is a proxy: the store has no explicit
"reviewer opened this document" event, so review time is measured from
document upload to the first correction submitted for it. Documents with
no corrections (auto-approved, or reviewed and left unchanged) don't
contribute a sample.
"""
from __future__ import annotations

from datetime import datetime

from app.core.models import RoutingDecision
from app.intake.store import document_store
from app.review.models import FieldAccuracyStat, ReviewAnalytics
from app.review.store import correction_store
from app.validation.store import validation_result_store


def compute_review_analytics() -> ReviewAnalytics:
    documents = document_store.all()
    validation_results = [validation_result_store.get(d.id) for d in documents]
    validation_results = [v for v in validation_results if v is not None]

    total_documents = len(validation_results)
    auto_approved = sum(1 for v in validation_results if v.routing == RoutingDecision.AUTO_APPROVED)
    needs_review = total_documents - auto_approved
    auto_approval_rate = auto_approved / total_documents if total_documents else 0.0

    corrections = correction_store.all()

    field_counts: dict[str, int] = {}
    for correction in corrections:
        field_counts[correction.field] = field_counts.get(correction.field, 0) + 1
    field_accuracy = [
        FieldAccuracyStat(field=field, correction_count=count)
        for field, count in sorted(field_counts.items(), key=lambda item: item[1], reverse=True)
    ]

    review_times: list[float] = []
    seen_documents: set[str] = set()
    for correction in sorted(corrections, key=lambda c: c.corrected_at):
        if correction.document_id in seen_documents:
            continue
        seen_documents.add(correction.document_id)
        document = document_store.get(correction.document_id)
        if document is None:
            continue
        opened_at = datetime.fromisoformat(document.uploaded_at)
        closed_at = datetime.fromisoformat(correction.corrected_at)
        review_times.append((closed_at - opened_at).total_seconds())
    average_review_time_seconds = sum(review_times) / len(review_times) if review_times else None

    return ReviewAnalytics(
        total_documents=total_documents,
        auto_approved=auto_approved,
        needs_review=needs_review,
        auto_approval_rate=auto_approval_rate,
        total_corrections=len(corrections),
        average_review_time_seconds=average_review_time_seconds,
        field_accuracy=field_accuracy,
    )
