"""AI Output Policy Guardrail Service — reviews LLM outputs before users
see them and returns approve / approve_with_warning / rewrite / block /
human_review, with the findings that produced the decision.

Endpoints:
  GET  /health                      readiness probe
  POST /v1/review                   review a candidate LLM output against all policies
  GET  /v1/audit/queue              blocked/uncertain decisions awaiting human review
  POST /v1/audit/{request_id}/review   record a reviewer's decision on an audit entry
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.audit import AuditLog, AuditLogEntry, ReviewAction
from app.core.config import settings
from app.core.models import ReviewRequest, ReviewResponse
from app.core.rate_limit import RateLimiter
from app.judge.client import OpenAIJudgeClient, StubJudgeClient
from app.judge.review import PolicyJudge
from app.policies.store import PolicyStore
from app.review.engine import ReviewEngine
from app.validators.forbidden import ForbiddenTermsStore

app = FastAPI(title="AI Output Policy Guardrail Service", version="0.1.0")

_limiter = RateLimiter(settings.rate_limit_per_minute)
_policy_store = PolicyStore.load(settings.policies_path)
_forbidden_store = ForbiddenTermsStore.load(settings.forbidden_terms_path)
_judge_client = OpenAIJudgeClient(api_key=settings.openai_api_key) if settings.openai_api_key else StubJudgeClient()
_judge = PolicyJudge(_policy_store, _judge_client)
_audit_log = AuditLog()
_engine = ReviewEngine(_policy_store, _forbidden_store, _judge, _audit_log)


class ReviewDecisionRequest(BaseModel):
    reviewer: str = Field(min_length=1, max_length=64)
    action: ReviewAction
    note: str | None = Field(default=None, max_length=2000)


def _rate_limited(request: Request) -> bool:
    client_key = request.client.host if request.client else "unknown"
    return not _limiter.allow(client_key)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/review", response_model=ReviewResponse)
def review(req: ReviewRequest, request: Request) -> ReviewResponse:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    return _engine.review(req)


@app.get("/v1/audit/queue", response_model=list[AuditLogEntry])
def audit_queue(request: Request) -> list[AuditLogEntry]:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    return _audit_log.pending_review()


@app.post("/v1/audit/{request_id}/review", response_model=AuditLogEntry)
def submit_review(request_id: str, body: ReviewDecisionRequest, request: Request) -> AuditLogEntry:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    entry = _audit_log.submit_review(request_id, body.reviewer, body.action, body.note)
    if entry is None:
        raise HTTPException(status_code=404, detail="Audit entry not found.")
    return entry
