from fastapi.testclient import TestClient

from app.main import app
from tests.pdf_builder import build_text_pdf


def test_extract_runs_ocr_automatically_and_returns_fields():
    data = build_text_pdf(["Invoice Number: INV-1\nVendor: Acme\nTotal: $10.00"])
    with TestClient(app) as client:
        upload = client.post("/v1/documents", files={"file": ("bill.pdf", data, "application/pdf")})
        document_id = upload.json()["id"]
        assert upload.json()["document_type"] == "invoice"

        r = client.post(f"/v1/documents/{document_id}/extract")
        assert r.status_code == 200
        body = r.json()
        assert body["document_type"] == "invoice"
        assert body["fields"]["vendor"]["value"] == "Acme"
        assert body["fields"]["total"]["value"] == 10.0
        assert body["conflicts"] == []


def test_extract_unknown_document_type_returns_422():
    data = build_text_pdf(["nothing recognizable here at all"])
    with TestClient(app) as client:
        upload = client.post("/v1/documents", files={"file": ("mystery.pdf", data, "application/pdf")})
        document_id = upload.json()["id"]
        assert upload.json()["document_type"] == "unknown"

        r = client.post(f"/v1/documents/{document_id}/extract")
        assert r.status_code == 422


def test_extract_missing_document_404():
    with TestClient(app) as client:
        r = client.post("/v1/documents/does-not-exist/extract")
        assert r.status_code == 404
