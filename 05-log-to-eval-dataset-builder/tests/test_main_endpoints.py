from fastapi.testclient import TestClient

from app.main import _candidate_store, _edit_log_store, _log_store, app


def _client() -> TestClient:
    _log_store.clear()
    _candidate_store.clear()
    _edit_log_store.clear()
    return TestClient(app)


def test_seed_logs():
    client = _client()
    r = client.post("/v1/logs/seed", json={"n": 100, "seed": 1})
    assert r.status_code == 200
    body = r.json()
    assert body["created"] == 100
    assert body["total_logs"] == 100


def test_ingest_single_log_redacts_pii():
    client = _client()
    r = client.post(
        "/v1/logs",
        json={
            "timestamp": "2026-01-01T00:00:00Z",
            "feature": "crm_note_summary",
            "prompt": "Contact jane.doe@example.com about the refund.",
            "response": "Will reach out shortly.",
            "model": "gpt-4o-mini",
            "latency_ms": 150.0,
            "input_tokens": 30,
            "output_tokens": 10,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "jane.doe@example.com" not in body["prompt"]
    assert body["redacted"] is True


def test_list_logs_filter_by_feature():
    client = _client()
    client.post("/v1/logs/seed", json={"n": 100, "seed": 1})
    r = client.get("/v1/logs", params={"feature": "crm_note_summary"})
    assert r.status_code == 200
    logs = r.json()
    assert len(logs) > 0
    assert all(log["feature"] == "crm_note_summary" for log in logs)


def test_sample_endpoint_modes():
    client = _client()
    client.post("/v1/logs/seed", json={"n": 100, "seed": 1})
    for mode in ("random", "failure_biased", "diversity"):
        r = client.post("/v1/sample", json={"mode": mode, "n": 10, "seed": 1})
        assert r.status_code == 200
        assert len(r.json()) == 10


def test_clusters_endpoint_requires_logs():
    client = _client()
    r = client.get("/v1/clusters")
    assert r.status_code == 400


def test_clusters_endpoint_returns_labeled_clusters():
    client = _client()
    client.post("/v1/logs/seed", json={"n": 100, "seed": 1})
    r = client.get("/v1/clusters", params={"k": 4})
    assert r.status_code == 200
    clusters = r.json()
    assert len(clusters) == 4
    assert sum(c["size"] for c in clusters) == 100


def test_candidates_endpoint():
    client = _client()
    client.post("/v1/logs/seed", json={"n": 100, "seed": 1})
    r = client.get("/v1/candidates", params={"top_n": 10})
    assert r.status_code == 200
    candidates = r.json()
    assert len(candidates) == 10
    scores = [c["score"] for c in candidates]
    assert scores == sorted(scores, reverse=True)


def test_generate_labels_and_list():
    client = _client()
    seed_resp = client.post("/v1/logs/seed", json={"n": 20, "seed": 1})
    log_ids = [log["id"] for log in client.get("/v1/logs", params={"limit": 5}).json()]
    assert seed_resp.status_code == 200

    r = client.post("/v1/labels/generate", json={"log_ids": log_ids})
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] + body["rejected_duplicates"] == len(log_ids)
    assert len(body["generated"]) == len(log_ids)

    listed = client.get("/v1/labels")
    assert listed.status_code == 200
    assert len(listed.json()) == len(log_ids)


def test_generate_labels_unknown_log_id_404():
    client = _client()
    r = client.post("/v1/labels/generate", json={"log_ids": ["does-not-exist"]})
    assert r.status_code == 404


def test_generate_labels_dedupes_identical_seeded_logs():
    client = _client()
    client.post("/v1/logs/seed", json={"n": 5, "seed": 1})
    log_ids = [log["id"] for log in client.get("/v1/logs").json()]
    r1 = client.post("/v1/labels/generate", json={"log_ids": log_ids})
    assert r1.json()["accepted"] + r1.json()["rejected_duplicates"] == len(log_ids)


def test_review_queue_and_decide_lifecycle():
    client = _client()
    client.post("/v1/logs/seed", json={"n": 30, "seed": 7})
    log_ids = [log["id"] for log in client.get("/v1/logs", params={"limit": 30}).json()]
    client.post("/v1/labels/generate", json={"log_ids": log_ids})

    queue = client.get("/v1/review/queue")
    assert queue.status_code == 200
    items = queue.json()
    assert len(items) > 0
    first = items[0]
    assert first["candidate"]["review_status"] == "draft"
    assert first["log"]["id"] == first["candidate"]["log_id"]

    candidate_id = first["candidate"]["id"]
    decide = client.post(
        "/v1/review/decide",
        json={"candidate_id": candidate_id, "action": "approve", "reviewer": "alex", "reason": "Looks right."},
    )
    assert decide.status_code == 200
    assert decide.json()["candidate"]["review_status"] == "approved"

    queue_after = client.get("/v1/review/queue").json()
    assert candidate_id not in {item["candidate"]["id"] for item in queue_after}

    edits = client.get("/v1/review/edits", params={"candidate_id": candidate_id})
    assert edits.status_code == 200
    assert len(edits.json()) == 1
    assert edits.json()[0]["reviewer"] == "alex"


def test_review_decide_edit_action_changes_fields():
    client = _client()
    client.post("/v1/logs/seed", json={"n": 30, "seed": 7})
    log_ids = [log["id"] for log in client.get("/v1/logs", params={"limit": 30}).json()]
    client.post("/v1/labels/generate", json={"log_ids": log_ids})
    candidate_id = client.get("/v1/review/queue").json()[0]["candidate"]["id"]

    resp = client.post(
        "/v1/review/decide",
        json={
            "candidate_id": candidate_id,
            "action": "edit",
            "reviewer": "sam",
            "reason": "Clarified wording.",
            "edits": {"expected_behavior": "Give a specific, actionable resolution."},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["candidate"]["review_status"] == "approved"
    assert body["candidate"]["expected_behavior"] == "Give a specific, actionable resolution."
    assert body["edit_log"]["changed_fields"][0]["field"] == "expected_behavior"


def test_review_decide_unknown_candidate_404():
    client = _client()
    r = client.post(
        "/v1/review/decide",
        json={"candidate_id": "does-not-exist", "action": "approve", "reviewer": "alex", "reason": "n/a"},
    )
    assert r.status_code == 404


def test_review_deprecate_requires_approved_first():
    client = _client()
    client.post("/v1/logs/seed", json={"n": 30, "seed": 7})
    log_ids = [log["id"] for log in client.get("/v1/logs", params={"limit": 30}).json()]
    client.post("/v1/labels/generate", json={"log_ids": log_ids})
    candidate_id = client.get("/v1/review/queue").json()[0]["candidate"]["id"]

    blocked = client.post(
        "/v1/review/deprecate", json={"candidate_id": candidate_id, "reviewer": "alex", "reason": "superseded"}
    )
    assert blocked.status_code == 400

    client.post(
        "/v1/review/decide",
        json={"candidate_id": candidate_id, "action": "approve", "reviewer": "alex", "reason": "ok"},
    )
    deprecated = client.post(
        "/v1/review/deprecate", json={"candidate_id": candidate_id, "reviewer": "alex", "reason": "superseded by v2"}
    )
    assert deprecated.status_code == 200
    assert deprecated.json()["candidate"]["review_status"] == "deprecated"
