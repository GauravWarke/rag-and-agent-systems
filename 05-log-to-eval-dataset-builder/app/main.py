"""Production Log-to-Eval Dataset Builder — mines production-like LLM
logs, samples the highest-value interactions, clusters them into
topics, and auto-generates candidate eval labels with a dedup pass
against the growing dataset.

Endpoints:
  GET  /health                readiness probe
  POST /v1/logs               ingest one log entry (validated + PII-redacted)
  POST /v1/logs/seed          seed the store with synthetic logs
  GET  /v1/logs                list ingested logs (optionally filtered by feature)
  POST /v1/sample             sample logs (random / failure_biased / diversity)
  GET  /v1/clusters           cluster logged prompts into labeled topics
  GET  /v1/candidates         rank logs by how valuable they'd be as eval cases
  POST /v1/labels/generate    propose eval labels for a set of logs, deduped
  GET  /v1/labels             list every generated label candidate (accepted + rejected)
  GET  /v1/review/queue       list candidates awaiting human review
  POST /v1/review/decide      approve, edit, or reject a reviewed candidate
  GET  /v1/review/edits       list the reviewer edit/decision history
  POST /v1/review/deprecate   mark an approved case deprecated
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query, Request

from app.core.config import settings
from app.core.models import (
    ClusterInfo,
    DeprecateRequest,
    EvalCandidate,
    GenerateLabelsRequest,
    GenerateLabelsResponse,
    HighValueCandidate,
    LogEntry,
    LogIngestRequest,
    ReviewDecisionRequest,
    ReviewDecisionResponse,
    ReviewEditLogEntry,
    ReviewQueueItem,
    SampleRequest,
    SeedLogsRequest,
    SeedLogsResponse,
)
from app.core.rate_limit import RateLimiter
from app.labels.client import LabelClient, OpenAILabelClient, StubLabelClient
from app.labels.dedupe import EvalCandidateStore, dedupe_and_add
from app.labels.generator import generate_label
from app.logs.store import LogStore
from app.logs.synthetic import generate_synthetic_logs
from app.review.decisions import ReviewEditLogStore, apply_decision, deprecate_candidate
from app.review.queue import build_queue
from app.sampling.candidates import identify_candidates
from app.sampling.cluster import cluster_assignments, cluster_logs
from app.sampling.sampler import diversity_sample, failure_biased_sample, random_sample

app = FastAPI(title="Production Log-to-Eval Dataset Builder", version="0.1.0")

_limiter = RateLimiter(settings.rate_limit_per_minute)
_log_store = LogStore()
_candidate_store = EvalCandidateStore()
_edit_log_store = ReviewEditLogStore()
_label_client: LabelClient = (
    OpenAILabelClient(api_key=settings.openai_api_key) if settings.openai_api_key else StubLabelClient()
)

# Features considered high-impact for candidate scoring — informs which
# clusters get prioritized for eval-label generation first.
_HIGH_IMPACT_FEATURES = {"support_reply_draft", "ticket_triage"}


def _rate_limited(request: Request) -> bool:
    client_key = request.client.host if request.client else "unknown"
    return not _limiter.allow(client_key)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/logs", response_model=LogEntry)
def ingest_log(req: LogIngestRequest, request: Request) -> LogEntry:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    return _log_store.add(req)


@app.post("/v1/logs/seed", response_model=SeedLogsResponse)
def seed_logs(req: SeedLogsRequest, request: Request) -> SeedLogsResponse:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    synthetic = generate_synthetic_logs(n=req.n, seed=req.seed)
    for entry in synthetic:
        _log_store.add_entry(entry)
    return SeedLogsResponse(created=len(synthetic), total_logs=len(_log_store))


@app.get("/v1/logs", response_model=list[LogEntry])
def list_logs(request: Request, feature: str | None = None, limit: int = Query(default=100, ge=1, le=2000)) -> list[LogEntry]:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    logs = _log_store.by_feature(feature) if feature else _log_store.all()
    return logs[:limit]


@app.post("/v1/sample", response_model=list[LogEntry])
def sample_logs(req: SampleRequest, request: Request) -> list[LogEntry]:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    logs = _log_store.by_feature(req.feature) if req.feature else _log_store.all()
    if req.mode == "random":
        return random_sample(logs, req.n, req.seed)
    if req.mode == "failure_biased":
        return failure_biased_sample(logs, req.n, req.seed)
    return diversity_sample(logs, req.n, req.seed)


@app.get("/v1/clusters", response_model=list[ClusterInfo])
def get_clusters(request: Request, k: int | None = Query(default=None, ge=2, le=50)) -> list[ClusterInfo]:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    if len(_log_store) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 logs to cluster. Seed logs first.")
    return cluster_logs(_log_store.all(), k=k)


def _covered_cluster_ids(logs: list[LogEntry]) -> set[int]:
    """Cluster ids that already have at least one accepted eval candidate."""
    accepted_log_ids = {c.log_id for c in _candidate_store.accepted()}
    if not accepted_log_ids:
        return set()
    assignments, _vectors, _k = cluster_assignments(logs)
    return {int(assignments[i]) for i, log in enumerate(logs) if log.id in accepted_log_ids}


@app.get("/v1/candidates", response_model=list[HighValueCandidate])
def get_candidates(request: Request, top_n: int = Query(default=20, ge=1, le=500)) -> list[HighValueCandidate]:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    if len(_log_store) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 logs to score. Seed logs first.")
    logs = _log_store.all()
    return identify_candidates(
        logs,
        high_impact_features=_HIGH_IMPACT_FEATURES,
        covered_cluster_ids=_covered_cluster_ids(logs),
        top_n=top_n,
    )


@app.post("/v1/labels/generate", response_model=GenerateLabelsResponse)
def generate_labels(req: GenerateLabelsRequest, request: Request) -> GenerateLabelsResponse:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")

    high_value_ids = {c.log_id for c in identify_candidates(_log_store.all(), top_n=len(_log_store) or 1)}

    generated = []
    for log_id in req.log_ids:
        log = _log_store.get(log_id)
        if log is None:
            raise HTTPException(status_code=404, detail=f"Log '{log_id}' not found.")
        proposed = generate_label(log, _label_client, important=log_id in high_value_ids)
        candidate = dedupe_and_add(log, proposed, _candidate_store)
        generated.append(candidate)

    accepted = sum(1 for c in generated if c.status == "accepted")
    return GenerateLabelsResponse(
        generated=generated, accepted=accepted, rejected_duplicates=len(generated) - accepted
    )


@app.get("/v1/labels", response_model=list[EvalCandidate])
def list_labels(request: Request) -> list[EvalCandidate]:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    return _candidate_store.all()


@app.get("/v1/review/queue", response_model=list[ReviewQueueItem])
def review_queue(request: Request) -> list[ReviewQueueItem]:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    return build_queue(_candidate_store, _log_store)


@app.post("/v1/review/decide", response_model=ReviewDecisionResponse)
def review_decide(req: ReviewDecisionRequest, request: Request) -> ReviewDecisionResponse:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    try:
        return apply_decision(req, _candidate_store, _edit_log_store, now=datetime.now(timezone.utc))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/review/edits", response_model=list[ReviewEditLogEntry])
def review_edits(request: Request, candidate_id: str | None = None) -> list[ReviewEditLogEntry]:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    if candidate_id:
        return _edit_log_store.for_candidate(candidate_id)
    return _edit_log_store.all()


@app.post("/v1/review/deprecate", response_model=ReviewDecisionResponse)
def review_deprecate(req: DeprecateRequest, request: Request) -> ReviewDecisionResponse:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    try:
        return deprecate_candidate(req, _candidate_store, _edit_log_store, now=datetime.now(timezone.utc))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
