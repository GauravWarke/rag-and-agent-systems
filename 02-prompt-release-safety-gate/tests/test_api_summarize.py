from fastapi.testclient import TestClient

from app.main import app


def test_summarize_happy_path():
    with TestClient(app) as client:
        r = client.post("/summarize", json={"note": "My invoice total looks wrong, please check it."})
        assert r.status_code == 200
        body = r.json()
        assert body["result"]["sentiment"] in {"negative", "neutral", "frustrated", "positive"}
        assert body["meta"]["prompt_version"] == "v1"


def test_summarize_can_select_candidate_prompt_version():
    with TestClient(app) as client:
        r = client.post(
            "/summarize",
            json={"note": "The export feature is broken again.", "prompt_version": "crm_summary_v2"},
        )
        assert r.status_code == 200
        assert r.json()["meta"]["prompt_version"] == "v2"


def test_summarize_unknown_prompt_version_returns_404():
    with TestClient(app) as client:
        r = client.post("/summarize", json={"note": "hello", "prompt_version": "does_not_exist"})
        assert r.status_code == 404


def test_summarize_rejects_empty_note():
    with TestClient(app) as client:
        r = client.post("/summarize", json={"note": ""})
        assert r.status_code == 422


def test_summarize_rejects_oversized_note():
    with TestClient(app) as client:
        r = client.post("/summarize", json={"note": "x" * 5000})
        assert r.status_code == 422
