"""Support Knowledge Copilot API.

Endpoints:
  GET  /health   readiness probe
  POST /ask      answer a support question with verified citations
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request

from app.core.config import settings
from app.core.models import AskRequest, AskResponse
from app.core.rate_limit import RateLimiter
from app.generation.answer import generate
from app.ingestion.loader import load_sample_corpus
from app.retrieval.hybrid import HybridRetriever

_retriever = HybridRetriever()
_limiter = RateLimiter(settings.rate_limit_per_minute)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _retriever.index(load_sample_corpus())
    yield


app = FastAPI(title="Support Knowledge Copilot", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, request: Request) -> AskResponse:
    client_key = request.client.host if request.client else "unknown"
    if not _limiter.allow(client_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")

    retrieved = _retriever.retrieve(req.question, strategy=req.strategy, access_level=req.access_level)
    return generate(req.question, retrieved)
