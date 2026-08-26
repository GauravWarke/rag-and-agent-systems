import io

from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import settings
from app.main import app


def _png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (800, 1000), color=(200, 200, 200)).save(buf, format="PNG")
    return buf.getvalue()


def test_run_ocr_on_uploaded_document(monkeypatch):
    monkeypatch.setattr(settings, "ocr_engine", "stub")
    with TestClient(app) as client:
        upload = client.post("/v1/documents", files={"file": ("scan.png", _png_bytes(), "image/png")})
        document_id = upload.json()["id"]

        r = client.post(f"/v1/documents/{document_id}/ocr")
        assert r.status_code == 200
        body = r.json()
        assert body["document_id"] == document_id
        assert len(body["pages"]) == 1
        assert body["pages"][0]["source"] == "vision_fallback"


def test_run_ocr_on_missing_document_404():
    with TestClient(app) as client:
        r = client.post("/v1/documents/does-not-exist/ocr")
        assert r.status_code == 404
