"""Support Knowledge Copilot API.

Endpoints:
  GET  /health   readiness probe
  POST /ask      answer a support question with verified citations
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.models import AskRequest, AskResponse
from app.generation.answer import generate
from app.ingestion.loader import load_sample_corpus
from app.retrieval.hybrid import HybridRetriever

_retriever = HybridRetriever()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _retriever.index(load_sample_corpus())
    yield


app = FastAPI(title="Support Knowledge Copilot", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    retrieved = _retriever.retrieve(req.question, strategy=req.strategy)
    return generate(req.question, retrieved)
