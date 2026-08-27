from fastapi.testclient import TestClient

from app.main import app
from tests.pdf_builder import build_text_pdf


def test_review_packet_includes_fields_pages_and_issues():
    text = (
        "Invoice Number: INV-1\nVendor: Acme Corp\nInvoice Date: 2026-01-05\n"
        "Subtotal: $100.00\nTax: $8.00\nTotal: $108.00"
    )
    data = build_text_pdf([text])
    with TestClient(app) as client:
        upload = client.post("/v1/documents", files={"file": ("bill.pdf", data, "application/pdf")})
        document_id = upload.json()["id"]

        r = client.get(f"/v1/documents/{document_id}/review")
        assert r.status_code == 200
        body = r.json()
        assert body["document_id"] == document_id
        assert body["fields"]["vendor"]["value"] == "Acme Corp"
        assert body["confidence"] == "high"
        assert body["routing"] == "auto_approved"
        assert body["issues"] == []
        assert len(body["pages"]) == 1
        assert body["pages"][0]["page_number"] == 1


def test_review_packet_runs_validation_automatically_when_absent():
    data = build_text_pdf(["Vendor: Acme Corp\nSubtotal: $10.00\nTax: $1.00\nTotal: $99.00"])
    with TestClient(app) as client:
        upload = client.post("/v1/documents", files={"file": ("bill.pdf", data, "application/pdf")})
        document_id = upload.json()["id"]

        r = client.get(f"/v1/documents/{document_id}/review")
        assert r.status_code == 200
        body = r.json()
        assert body["routing"] == "needs_review"
        assert len(body["issues"]) > 0


def test_review_packet_missing_document_404():
    with TestClient(app) as client:
        r = client.get("/v1/documents/does-not-exist/review")
        assert r.status_code == 404


def test_page_image_round_trips_for_a_born_digital_pdf_page():
    data = build_text_pdf(["Vendor: Acme Corp\nTotal: $10.00"])
    with TestClient(app) as client:
        upload = client.post("/v1/documents", files={"file": ("bill.pdf", data, "application/pdf")})
        document_id = upload.json()["id"]

        r = client.get(f"/v1/documents/{document_id}/pages/1/image")
        # A born-digital PDF page has no rasterized normalized image (Phase 1
        # skips OCR for it entirely), so no image is available; scanned/image
        # uploads do produce one.
        assert r.status_code == 404


def test_page_image_missing_page_number_404():
    data = build_text_pdf(["Vendor: Acme Corp\nTotal: $10.00"])
    with TestClient(app) as client:
        upload = client.post("/v1/documents", files={"file": ("bill.pdf", data, "application/pdf")})
        document_id = upload.json()["id"]

        r = client.get(f"/v1/documents/{document_id}/pages/99/image")
        assert r.status_code == 404


def test_page_image_missing_document_404():
    with TestClient(app) as client:
        r = client.get("/v1/documents/does-not-exist/pages/1/image")
        assert r.status_code == 404
