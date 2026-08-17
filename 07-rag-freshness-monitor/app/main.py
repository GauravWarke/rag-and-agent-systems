"""RAG Freshness and Drift Monitor.

Watches a small RAG knowledge base for stale sources, changed content, and
retrieval drift, and tells the team when the index needs rebuilding.

Endpoints:
  GET  /health                readiness probe
  POST /v1/index/build        (re)build the index manifest from the corpus on disk
  GET  /v1/index/manifest     return the currently saved manifest
  POST /v1/freshness/scan     diff the corpus against the saved manifest, with priority
  POST /v1/probes/run         run the probe set against the current corpus,
                               and report drift against the previous run
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request

from app.core.config import settings
from app.core.models import DriftReport, FreshnessReport, IndexManifest, ProbeRunSummary
from app.core.rate_limit import RateLimiter
from app.drift.probes import compare_runs, load_probes, run_probes
from app.freshness.diff import diff_against_manifest
from app.freshness.priority import prioritize_diff
from app.indexing.chunker import build_chunks
from app.indexing.manifest import build_manifest, load_manifest, save_manifest

_BASE_DIR = Path(__file__).resolve().parents[1]


def _resolve(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else _BASE_DIR / path


app = FastAPI(title="RAG Freshness and Drift Monitor", version="0.1.0")

_limiter = RateLimiter(settings.rate_limit_per_minute)
_last_probe_run: ProbeRunSummary | None = None


def _rate_limited(request: Request) -> bool:
    client_key = request.client.host if request.client else "unknown"
    return not _limiter.allow(client_key)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/index/build", response_model=IndexManifest)
def build_index(request: Request) -> IndexManifest:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    manifest = build_manifest(
        docs_dir=_resolve(settings.docs_dir),
        docs_meta_path=_resolve(settings.docs_meta_path),
        embedding_model=settings.embedding_model,
        embedding_version=settings.embedding_version,
        chunking_strategy=settings.chunking_strategy,
    )
    save_manifest(manifest, _resolve(settings.manifest_path))
    return manifest


@app.get("/v1/index/manifest", response_model=IndexManifest)
def get_manifest(request: Request) -> IndexManifest:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    manifest = load_manifest(_resolve(settings.manifest_path))
    if manifest is None:
        raise HTTPException(status_code=404, detail="No manifest built yet. Call POST /v1/index/build first.")
    return manifest


@app.post("/v1/freshness/scan", response_model=FreshnessReport)
def freshness_scan(request: Request) -> FreshnessReport:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    manifest = load_manifest(_resolve(settings.manifest_path))
    if manifest is None:
        raise HTTPException(status_code=404, detail="No manifest built yet. Call POST /v1/index/build first.")
    diff = diff_against_manifest(manifest, _resolve(settings.docs_dir), _resolve(settings.docs_meta_path))
    return FreshnessReport(diff=diff, prioritized=prioritize_diff(diff))


@app.post("/v1/probes/run", response_model=ProbeRunSummary)
def probes_run(request: Request) -> ProbeRunSummary:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    global _last_probe_run
    probes = load_probes(_resolve(settings.probes_path))
    chunks = build_chunks(_resolve(settings.docs_dir), _resolve(settings.docs_meta_path), settings.embedding_version)
    current = run_probes(probes, chunks)
    _last_probe_run = current
    return current


@app.post("/v1/probes/drift", response_model=DriftReport)
def probes_drift(request: Request) -> DriftReport:
    """Re-run the probe set now and compare it to the last `/v1/probes/run`
    snapshot, to see whether retrieval results changed in between."""
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    if _last_probe_run is None:
        raise HTTPException(status_code=404, detail="No probe runs recorded yet. Call POST /v1/probes/run first.")
    probes = load_probes(_resolve(settings.probes_path))
    chunks = build_chunks(_resolve(settings.docs_dir), _resolve(settings.docs_meta_path), settings.embedding_version)
    current = run_probes(probes, chunks)
    return compare_runs(_last_probe_run, current)
