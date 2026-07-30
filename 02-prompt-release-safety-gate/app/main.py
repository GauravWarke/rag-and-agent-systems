"""Prompt Release Safety Gate — CRM note summarizer under test.

Endpoints:
  GET  /health      readiness probe
  POST /summarize    turn a messy customer note into a structured CRM summary
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from pydantic import ValidationError

from app.core.config import settings
from app.core.models import (
    GenerationMeta,
    NoteSummary,
    SummarizeRequest,
    SummarizeResponse,
)
from app.core.rate_limit import RateLimiter
from app.generation.summarizer import run_prompt
from app.prompts.loader import load_prompt

app = FastAPI(title="Prompt Release Safety Gate", version="0.1.0")

_limiter = RateLimiter(settings.rate_limit_per_minute)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/summarize", response_model=SummarizeResponse)
def summarize(req: SummarizeRequest, request: Request) -> SummarizeResponse:
    client_key = request.client.host if request.client else "unknown"
    if not _limiter.allow(client_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")

    prompt_name = req.prompt_version or settings.baseline_prompt
    try:
        prompt = load_prompt(prompt_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    raw, meta_dict = run_prompt(req.note, prompt)
    if meta_dict["error"]:
        raise HTTPException(status_code=502, detail=meta_dict["error"])

    try:
        result = NoteSummary.model_validate(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=502, detail=f"Prompt output failed schema validation: {exc}") from exc

    return SummarizeResponse(result=result, meta=GenerationMeta.model_validate(meta_dict))
