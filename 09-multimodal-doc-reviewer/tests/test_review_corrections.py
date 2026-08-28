from fastapi.testclient import TestClient

from app.main import app
from tests.pdf_builder import build_text_pdf


def _upload_and_review(client: TestClient, text: str) -> str:
    data = build_text_pdf([text])
    upload = client.post("/v1/documents", files={"file": ("bill.pdf", data, "application/pdf")})
    document_id = upload.json()["id"]
    client.get(f"/v1/documents/{document_id}/review")
    return document_id


def test_submit_correction_updates_field_and_is_returned_by_review():
    with TestClient(app) as client:
        document_id = _upload_and_review(
            client,
            "Invoice Number: INV-1\nVendor: Acme Corp\nSubtotal: $100.00\nTax: $8.00\nTotal: $108.00",
        )

        r = client.post(
            f"/v1/documents/{document_id}/review/corrections",
            json={"field": "vendor", "corrected_value": "Acme Corporation", "reviewer": "alice", "reason": "typo"},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["document_id"] == document_id
        assert body["field"] == "vendor"
        assert body["original_value"]["value"] == "Acme Corp"
        assert body["corrected_value"] == "Acme Corporation"
        assert body["reviewer"] == "alice"

        review = client.get(f"/v1/documents/{document_id}/review").json()
        assert review["fields"]["vendor"]["value"] == "Acme Corporation"
        assert review["fields"]["vendor"]["source"] == "human_correction"


def test_submit_correction_on_list_field_replaces_whole_list():
    with TestClient(app) as client:
        document_id = _upload_and_review(client, "Invoice Number: INV-1\nVendor: Acme Corp\nTotal: $10.00")

        r = client.post(
            f"/v1/documents/{document_id}/review/corrections",
            json={"field": "line_items", "corrected_value": ["Widget x2"], "reviewer": "bob"},
        )
        assert r.status_code == 201
        assert r.json()["corrected_value"] == ["Widget x2"]

        review = client.get(f"/v1/documents/{document_id}/review").json()
        assert review["fields"]["line_items"] == ["Widget x2"]


def test_submit_correction_unknown_field_400():
    with TestClient(app) as client:
        document_id = _upload_and_review(client, "Vendor: Acme Corp\nTotal: $10.00")

        r = client.post(
            f"/v1/documents/{document_id}/review/corrections",
            json={"field": "not_a_real_field", "corrected_value": "x", "reviewer": "alice"},
        )
        assert r.status_code == 400


def test_submit_correction_missing_document_404():
    with TestClient(app) as client:
        r = client.post(
            "/v1/documents/does-not-exist/review/corrections",
            json={"field": "vendor", "corrected_value": "x", "reviewer": "alice"},
        )
        assert r.status_code == 404


def test_list_corrections_returns_submitted_history():
    with TestClient(app) as client:
        document_id = _upload_and_review(client, "Vendor: Acme Corp\nTotal: $10.00")

        client.post(
            f"/v1/documents/{document_id}/review/corrections",
            json={"field": "vendor", "corrected_value": "Acme Corporation", "reviewer": "alice"},
        )
        client.post(
            f"/v1/documents/{document_id}/review/corrections",
            json={"field": "total", "corrected_value": 12.5, "reviewer": "bob", "reason": "misread"},
        )

        r = client.get(f"/v1/documents/{document_id}/review/corrections")
        assert r.status_code == 200
        fields = {c["field"] for c in r.json()}
        assert fields == {"vendor", "total"}
