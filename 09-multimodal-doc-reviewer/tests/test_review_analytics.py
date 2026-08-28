from fastapi.testclient import TestClient

from app.main import app
from tests.pdf_builder import build_text_pdf


def _upload(client: TestClient, text: str) -> str:
    data = build_text_pdf([text])
    upload = client.post("/v1/documents", files={"file": ("bill.pdf", data, "application/pdf")})
    return upload.json()["id"]


def test_analytics_empty_when_no_documents():
    with TestClient(app) as client:
        r = client.get("/v1/review/analytics")
        assert r.status_code == 200
        body = r.json()
        assert body["total_documents"] == 0
        assert body["auto_approval_rate"] == 0.0
        assert body["total_corrections"] == 0
        assert body["average_review_time_seconds"] is None
        assert body["field_accuracy"] == []


def test_analytics_tracks_auto_approval_rate_and_corrections():
    with TestClient(app) as client:
        good_id = _upload(
            client,
            "Invoice Number: INV-1\nVendor: Acme Corp\nInvoice Date: 2026-01-05\n"
            "Subtotal: $100.00\nTax: $8.00\nTotal: $108.00",
        )
        client.get(f"/v1/documents/{good_id}/review")

        bad_id = _upload(client, "Vendor: Acme Corp\nSubtotal: $10.00\nTax: $1.00\nTotal: $99.00")
        client.get(f"/v1/documents/{bad_id}/review")
        client.post(
            f"/v1/documents/{bad_id}/review/corrections",
            json={"field": "total", "corrected_value": 11.0, "reviewer": "alice", "reason": "math error"},
        )

        r = client.get("/v1/review/analytics")
        assert r.status_code == 200
        body = r.json()
        assert body["total_documents"] == 2
        assert body["auto_approved"] == 1
        assert body["needs_review"] == 1
        assert body["auto_approval_rate"] == 0.5
        assert body["total_corrections"] == 1
        assert body["average_review_time_seconds"] is not None
        assert body["average_review_time_seconds"] >= 0
        assert body["field_accuracy"] == [{"field": "total", "correction_count": 1}]
