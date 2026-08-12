"""Regenerates the headline numbers in docs/case_study.md.

Runs the full flywheel end-to-end through the real FastAPI app (via
TestClient, no network, offline stub label/embedding clients): seed
synthetic production logs, score them for eval-candidate value,
auto-generate labels with dedup, simulate a human reviewer clearing the
review queue, then export the approved dataset and run it once. Run from
inside 05-log-to-eval-dataset-builder/:

    python docs/case_study_batch.py
"""
from __future__ import annotations

import random

from fastapi.testclient import TestClient

from app.main import (
    _candidate_store,
    _edit_log_store,
    _eval_run_store,
    _limiter,
    _log_store,
    app,
)

N_LOGS = 3000
TOP_N_CANDIDATES = 250
DIVERSITY_SAMPLE_N = 200
SEED = 7
GENERATE_BATCH_SIZE = 200


def _client() -> TestClient:
    _log_store.clear()
    _candidate_store.clear()
    _edit_log_store.clear()
    _eval_run_store.clear()
    _limiter.clear()
    # This script issues far more requests than the default per-minute cap
    # (meant for a single human/automation client, not a batch replay).
    _limiter.requests_per_minute = 100_000
    return TestClient(app)


def _simulate_review(client: TestClient, rng: random.Random) -> dict[str, int]:
    """Walk the human review queue and decide each draft, the way a
    reviewer would: approve the good ones, lightly edit a few, reject the
    rest. Deterministic given `rng` so the case study is reproducible."""
    decisions = {"approve": 0, "edit": 0, "reject": 0}
    queue = client.get("/v1/review/queue").json()
    for item in queue:
        candidate = item["candidate"]
        roll = rng.random()
        if roll < 0.75:
            action, edits = "approve", None
        elif roll < 0.90:
            action, edits = "edit", {"expected_behavior": candidate["expected_behavior"].strip() + " (clarified by reviewer)"}
        else:
            action, edits = "reject", None

        resp = client.post(
            "/v1/review/decide",
            json={
                "candidate_id": candidate["id"],
                "action": action,
                "reviewer": "dana",
                "reason": f"batch review: {action}",
                "edits": edits,
            },
        )
        resp.raise_for_status()
        decisions[action] += 1
    return decisions


def main() -> None:
    client = _client()
    rng = random.Random(SEED)

    seed_resp = client.post("/v1/logs/seed", json={"n": N_LOGS, "seed": SEED})
    seed_resp.raise_for_status()
    total_logs = seed_resp.json()["total_logs"]

    clusters = client.get("/v1/clusters").json()

    # High-value candidates (unusual, risky, or under-covered) plus a
    # diversity sample (farthest-point over prompt embeddings) so the
    # generated labels span more than just the failure modes — the same
    # mix of sampling modes a real dataset curator would combine.
    candidates_resp = client.get("/v1/candidates", params={"top_n": TOP_N_CANDIDATES})
    candidates_resp.raise_for_status()
    candidate_log_ids = [c["log_id"] for c in candidates_resp.json()]

    diversity_resp = client.post(
        "/v1/sample", json={"mode": "diversity", "n": DIVERSITY_SAMPLE_N, "seed": SEED}
    )
    diversity_resp.raise_for_status()
    diversity_log_ids = [log["id"] for log in diversity_resp.json()]

    candidate_log_ids = list(dict.fromkeys(candidate_log_ids + diversity_log_ids))

    generated = 0
    accepted = 0
    rejected_duplicates = 0
    for start in range(0, len(candidate_log_ids), GENERATE_BATCH_SIZE):
        batch = candidate_log_ids[start : start + GENERATE_BATCH_SIZE]
        resp = client.post("/v1/labels/generate", json={"log_ids": batch})
        resp.raise_for_status()
        body = resp.json()
        generated += len(body["generated"])
        accepted += body["accepted"]
        rejected_duplicates += body["rejected_duplicates"]

    labels = client.get("/v1/labels").json()
    auto_approved = sum(1 for c in labels if c["status"] == "accepted" and c["review_status"] == "approved")
    queued_for_review = sum(1 for c in labels if c["status"] == "accepted" and c["review_status"] == "draft")

    review_decisions = _simulate_review(client, rng)

    health = client.get("/v1/dataset/health").json()

    export_resp = client.get("/v1/export/jsonl")
    export_resp.raise_for_status()
    exported_lines = [line for line in export_resp.text.splitlines() if line.strip()]

    eval_resp = client.post("/v1/eval-runs/run")
    eval_resp.raise_for_status()
    eval_run = eval_resp.json()

    print(f"logs seeded: {total_logs}")
    print(f"clusters discovered: {len(clusters)}")
    print(f"candidate pool (high-value + diversity sample, deduped): {len(candidate_log_ids)}")
    print(f"labels generated: {generated}")
    print(f"accepted (novel): {accepted}")
    print(f"rejected as near-duplicates: {rejected_duplicates} ({rejected_duplicates / generated:.1%})")
    print(f"auto-approved (confidence >= threshold): {auto_approved}")
    print(f"queued for human review: {queued_for_review}")
    print(f"reviewer decisions: {review_decisions}")
    print(f"approved cases exported to JSONL: {len(exported_lines)}")
    print(f"dataset health: {health}")
    print(f"eval run: pass_rate={eval_run['pass_rate']:.1%} ({eval_run['passed']}/{eval_run['total_cases']})")


if __name__ == "__main__":
    main()
