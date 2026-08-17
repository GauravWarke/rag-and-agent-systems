import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.core.config import settings
from app.core.rate_limit import RateLimiter
from app.main import app

_REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def isolated_corpus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Copy the bundled corpus into a tmp dir and point settings at it, so
    tests that build/mutate the index never touch the real repo files."""
    docs_dir = tmp_path / "docs"
    shutil.copytree(_REPO_ROOT / "data" / "docs", docs_dir)
    meta_path = tmp_path / "docs_meta.json"
    shutil.copy(_REPO_ROOT / "data" / "docs_meta.json", meta_path)
    manifest_path = tmp_path / "index" / "manifest.json"

    monkeypatch.setattr(settings, "docs_dir", str(docs_dir))
    monkeypatch.setattr(settings, "docs_meta_path", str(meta_path))
    monkeypatch.setattr(settings, "manifest_path", str(manifest_path))
    monkeypatch.setattr(settings, "probes_path", str(_REPO_ROOT / "data" / "probes.json"))
    monkeypatch.setattr(main_module, "_limiter", RateLimiter(requests_per_minute=1000))
    monkeypatch.setattr(main_module, "_last_probe_run", None)
    return docs_dir


def test_manifest_404_before_build(isolated_corpus: Path):
    with TestClient(app) as client:
        r = client.get("/v1/index/manifest")
        assert r.status_code == 404


def test_freshness_scan_404_before_build(isolated_corpus: Path):
    with TestClient(app) as client:
        r = client.post("/v1/freshness/scan")
        assert r.status_code == 404


def test_build_index_then_get_manifest(isolated_corpus: Path):
    with TestClient(app) as client:
        built = client.post("/v1/index/build")
        assert built.status_code == 200
        assert len(built.json()["chunks"]) == 16

        fetched = client.get("/v1/index/manifest")
        assert fetched.status_code == 200
        assert fetched.json() == built.json()


def test_freshness_scan_detects_modified_section(isolated_corpus: Path):
    with TestClient(app) as client:
        client.post("/v1/index/build")

        policies_path = isolated_corpus / "policies.md"
        original = policies_path.read_text(encoding="utf-8")
        updated = original.replace(
            "Customers can request a refund within 30 days of purchase if the product has not been activated. "
            "Approved refunds are processed within 5 business days back to the original payment method.",
            "Refunds within 60 days now, a meaningfully different window.",
        )
        assert updated != original
        policies_path.write_text(updated, encoding="utf-8")

        r = client.post("/v1/freshness/scan")
        assert r.status_code == 200
        body = r.json()
        assert len(body["diff"]["modified"]) == 1
        assert body["diff"]["modified"][0]["chunk_id"] == "policies::refund-policy"
        assert body["diff"]["added"] == []
        assert body["diff"]["removed"] == []
        assert len(body["prioritized"]) == 1


def test_probes_run_returns_summary(isolated_corpus: Path):
    with TestClient(app) as client:
        r = client.post("/v1/probes/run")
        assert r.status_code == 200
        body = r.json()
        assert body["total_probes"] == 20
        assert 0.0 <= body["match_rate"] <= 1.0


def test_probes_drift_requires_prior_run(isolated_corpus: Path):
    with TestClient(app) as client:
        r = client.post("/v1/probes/drift")
        assert r.status_code == 404


def test_probes_drift_detects_removed_expected_chunk(isolated_corpus: Path):
    with TestClient(app) as client:
        first = client.post("/v1/probes/run")
        assert first.status_code == 200

        # Remove a section so a probe that used to match it must now drift.
        policies_text = (isolated_corpus / "policies.md").read_text(encoding="utf-8")
        without_refund = "\n".join(
            part for part in policies_text.split("\n\n") if "Refund Policy" not in part
        )
        (isolated_corpus / "policies.md").write_text(without_refund, encoding="utf-8")

        drift = client.post("/v1/probes/drift")
        assert drift.status_code == 200
        body = drift.json()
        drifted_ids = {d["probe_id"] for d in body["drifted"]}
        assert "p01" in drifted_ids or "p02" in drifted_ids


def test_rate_limit_returns_429(monkeypatch: pytest.MonkeyPatch, isolated_corpus: Path):
    monkeypatch.setattr(main_module, "_limiter", RateLimiter(requests_per_minute=1))
    with TestClient(app) as client:
        first = client.get("/v1/index/manifest")
        second = client.get("/v1/index/manifest")
        assert first.status_code in (200, 404)
        assert second.status_code == 429
