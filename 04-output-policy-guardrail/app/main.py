"""AI Output Policy Guardrail Service — reviews LLM outputs before users
see them and returns approve / approve_with_warning / rewrite / block /
human_review, with the findings that produced the decision.

Endpoints:
  GET  /health        readiness probe
  POST /v1/review     review a candidate LLM output against all policies
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request

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
_engine = ReviewEngine(_policy_store, _forbidden_store, _judge)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/review", response_model=ReviewResponse)
def review(req: ReviewRequest, request: Request) -> ReviewResponse:
    client_key = request.client.host if request.client else "unknown"
    if not _limiter.allow(client_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    return _engine.review(req)
