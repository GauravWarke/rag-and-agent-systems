"""Natural Language to API Assistant — turns natural-language requests into
schema-validated, risk-gated calls against a mock SaaS admin API
(customers, subscriptions, invoices, tickets, refunds).

Endpoints:
  GET  /health                              readiness probe
  GET  /biz/...                             mock business API (see /docs for the full OpenAPI schema)
  POST /v1/assistant/workflows              plan + validate + (execute or dry-run) a NL request
  GET  /v1/assistant/workflows              list assistant workflows
  GET  /v1/assistant/workflows/{id}         fetch one workflow
  POST /v1/assistant/workflows/{id}/resume  approve/reject a paused workflow
"""
from __future__ import annotations

from fastapi import FastAPI

from app.business_api.router import router as business_router
from app.planning.router import router as assistant_router

app = FastAPI(title="Natural Language to API Assistant", version="0.1.0")

app.include_router(business_router)
app.include_router(assistant_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
