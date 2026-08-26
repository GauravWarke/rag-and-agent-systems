import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from tests.pdf_builder import build_text_pdf


def _png_bytes(width=800, height=1000):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(180, 180, 180)).save(buf, format="PNG")
    return buf.getvalue()


def test_upload_image_document():
    with TestClient(app) as client:
        r = client.post(
            "/v1/documents",
            files={"file": ("invoice_scan.png", _png_bytes(), "image/png")},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["filename"] == "invoice_scan.png"
        assert body["page_count"] == 1
        assert body["document_type"] == "invoice"
        assert "normalized_image_png" not in body["pages"][0]
        assert body["pages"][0]["has_normalized_image"] is True


def test_upload_pdf_document():
    data = build_text_pdf(["Invoice Number: INV-1\nVendor: Acme\nTotal: $10.00"])
    with TestClient(app) as client:
        r = client.post(
            "/v1/documents",
            files={"file": ("bill.pdf", data, "application/pdf")},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["page_count"] == 1
        assert body["pages"][0]["source_format"] == "pdf_text"


def test_rejects_unsupported_content_type():
    with TestClient(app) as client:
        r = client.post("/v1/documents", files={"file": ("notes.txt", b"hello", "text/plain")})
        assert r.status_code == 415


def test_rejects_empty_file():
    with TestClient(app) as client:
        r = client.post("/v1/documents", files={"file": ("empty.png", b"", "image/png")})
        assert r.status_code == 400


def test_get_and_list_documents():
    with TestClient(app) as client:
        upload = client.post("/v1/documents", files={"file": ("a.png", _png_bytes(), "image/png")})
        document_id = upload.json()["id"]

        got = client.get(f"/v1/documents/{document_id}")
        assert got.status_code == 200
        assert got.json()["id"] == document_id

        listed = client.get("/v1/documents")
        assert listed.status_code == 200
        assert any(d["id"] == document_id for d in listed.json())


def test_get_missing_document_404():
    with TestClient(app) as client:
        r = client.get("/v1/documents/does-not-exist")
        assert r.status_code == 404
