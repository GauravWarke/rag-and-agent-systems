"""Portfolio walkthrough (Phase 6): pushes one messy scanned receipt all
the way through the pipeline — upload/preprocessing, OCR with a failed
vision fallback, structured extraction, validation, routing to human
review, and a reviewer's correction — and prints a readable transcript of
each stage. No API key or network access required, matching this repo's
offline-runnable-by-default convention: `OCR_ENGINE` is forced to the
deterministic `stub` engine for the duration of the demo so the outcome
does not depend on whether `tesseract` happens to be installed.
"""
from __future__ import annotations

import io

from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import settings
from app.main import app

FILENAME = "reimbursement_receipt_scan.jpg"


def _messy_receipt_image_bytes() -> bytes:
    """A small, low-contrast, sideways scan: below the 600x600 minimum
    resolution and tagged with an EXIF rotation, so both the resolution
    check and the rotation-correction step have something to report.
    """
    image = Image.new("RGB", (400, 300), color=(210, 205, 195))
    exif = Image.Exif()
    exif[0x0112] = 6  # rotated 90 degrees clockwise
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


def run_demo() -> str:
    lines: list[str] = ["=== Messy document walkthrough: reimbursement_receipt_scan.jpg ==="]
    original_ocr_engine = settings.ocr_engine
    settings.ocr_engine = "stub"
    try:
        with TestClient(app) as client:
            upload = client.post(
                "/v1/documents",
                files={"file": (FILENAME, _messy_receipt_image_bytes(), "image/jpeg")},
            )
            document = upload.json()
            document_id = document["id"]
            page = document["pages"][0]
            lines.append(f"\n-- Upload & preprocessing --\ndocument_type: {document['document_type']}")
            for step in page["preprocessing"]:
                lines.append(f"  [{step['name']}] {step['detail']}")
            for warning in page["warnings"]:
                lines.append(f"  WARNING: {warning}")

            ocr = client.post(f"/v1/documents/{document_id}/ocr").json()
            ocr_page = ocr["pages"][0]
            lines.append(f"\n-- OCR & vision fallback --\nsource: {ocr_page['source']}")
            if ocr_page["vision"]:
                lines.append(f"  vision fallback note: {ocr_page['vision']['note']}")

            extraction = client.post(f"/v1/documents/{document_id}/extract").json()
            lines.append(f"\n-- Structured extraction --\nfields: {extraction['fields']}")

            validation = client.post(f"/v1/documents/{document_id}/validate").json()
            lines.append(
                f"\n-- Validation & routing --\nconfidence: {validation['confidence']}, "
                f"routing: {validation['routing']}"
            )
            for issue in validation["issues"]:
                lines.append(f"  [{issue['severity']}] {issue['field']}: {issue['message']}")

            review = client.get(f"/v1/documents/{document_id}/review").json()
            lines.append(
                f"\n-- Human review --\n{len(review['issues'])} issue(s) sent a reviewer to look at "
                f"page 1 of {FILENAME}"
            )

            corrections = {
                "vendor": "Acme Corp",
                "purchase_date": "2026-08-20",
                "total": 42.50,
            }
            for field, value in corrections.items():
                client.post(
                    f"/v1/documents/{document_id}/review/corrections",
                    json={
                        "field": field,
                        "corrected_value": value,
                        "reviewer": "alex",
                        "reason": "read directly from the scanned image",
                    },
                )
            lines.append(f"reviewer 'alex' filled in: {corrections}")

            revalidated = client.post(f"/v1/documents/{document_id}/validate").json()
            lines.append(
                f"\n-- Re-validated after correction --\nconfidence: {revalidated['confidence']}, "
                f"routing: {revalidated['routing']}"
            )

            analytics = client.get("/v1/review/analytics").json()
            lines.append(
                f"\n-- Queue analytics --\nauto_approval_rate: {analytics['auto_approval_rate']:.0%}, "
                f"total_corrections: {analytics['total_corrections']}, "
                f"most-corrected field: {analytics['field_accuracy'][0]['field'] if analytics['field_accuracy'] else 'n/a'}"
            )
    finally:
        settings.ocr_engine = original_ocr_engine

    return "\n".join(lines)
