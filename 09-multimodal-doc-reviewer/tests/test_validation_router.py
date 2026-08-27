from fastapi.testclient import TestClient

from app.main import app
from tests.pdf_builder import build_text_pdf


def test_validate_clean_invoice_is_auto_approved():
    text = (
        "Invoice Number: INV-1\nVendor: Acme Corp\nInvoice Date: 2026-01-05\n"
        "Subtotal: $100.00\nTax: $8.00\nTotal: $108.00"
    )
    data = build_text_pdf([text])
    with TestClient(app) as client:
        upload = client.post("/v1/documents", files={"file": ("bill.pdf", data, "application/pdf")})
        document_id = upload.json()["id"]

        r = client.post(f"/v1/documents/{document_id}/validate")
        assert r.status_code == 200
        body = r.json()
        assert body["confidence"] == "high"
        assert body["routing"] == "auto_approved"
        assert body["issues"] == []


def test_validate_missing_fields_and_bad_total_needs_review():
    data = build_text_pdf(["Vendor: Acme Corp\nSubtotal: $100.00\nTax: $8.00\nTotal: $500.00"])
    with TestClient(app) as client:
        upload = client.post("/v1/documents", files={"file": ("bill.pdf", data, "application/pdf")})
        document_id = upload.json()["id"]

        r = client.post(f"/v1/documents/{document_id}/validate")
        assert r.status_code == 200
        body = r.json()
        assert body["confidence"] == "low"
        assert body["routing"] == "needs_review"
        fields_flagged = {issue["field"] for issue in body["issues"]}
        assert "invoice_number" in fields_flagged
        assert "invoice_date" in fields_flagged
        assert "total" in fields_flagged


def test_validate_unknown_vendor_only_is_medium_confidence():
    text = (
        "Invoice Number: INV-1\nVendor: Totally Unknown LLC\nInvoice Date: 2026-01-05\n"
        "Subtotal: $100.00\nTax: $8.00\nTotal: $108.00"
    )
    data = build_text_pdf([text])
    with TestClient(app) as client:
        upload = client.post("/v1/documents", files={"file": ("bill.pdf", data, "application/pdf")})
        document_id = upload.json()["id"]

        r = client.post(f"/v1/documents/{document_id}/validate")
        assert r.status_code == 200
        body = r.json()
        assert body["confidence"] == "medium"
        assert body["routing"] == "needs_review"
        assert len(body["issues"]) == 1
        assert body["issues"][0]["severity"] == "warning"


def test_validate_missing_document_404():
    with TestClient(app) as client:
        r = client.post("/v1/documents/does-not-exist/validate")
        assert r.status_code == 404


def test_validate_runs_extraction_automatically_when_absent():
    data = build_text_pdf(["Merchant: Acme Corp\nPurchase Date: 2026-01-05\nTotal: $10.00\nPayment Method: Cash"])
    with TestClient(app) as client:
        upload = client.post("/v1/documents", files={"file": ("receipt.pdf", data, "application/pdf")})
        document_id = upload.json()["id"]
        assert upload.json()["document_type"] == "reimbursement_receipt"

        r = client.post(f"/v1/documents/{document_id}/validate")
        assert r.status_code == 200
        assert r.json()["routing"] in {"auto_approved", "needs_review"}
