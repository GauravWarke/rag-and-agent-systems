"""Natural Language to API Assistant — turns natural-language requests into
schema-validated, risk-gated calls against a mock SaaS admin API
(customers, subscriptions, invoices, tickets, refunds).

Endpoints:
  GET  /health                              readiness probe
  GET  /biz/...                             mock business API (see /docs for the full OpenAPI schema)
  POST /v1/assistant/workflows              plan + validate + (execute or dry-run) a NL request
  GET  /v1/assistant/workflows              list assistant workflows
  GET  /v1/assistant/workflows/{id}         fetch one workflow
  GET  /v1/assistant/workflows/{id}/view    UI read-model: planned calls, dry-run, actions, result
  POST /v1/assistant/workflows/{id}/resume  approve/reject a paused workflow
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.business_api.router import router as business_router
from app.planning.router import router as assistant_router

app = FastAPI(
    title='Natural Language to API Assistant',
    description=(
        'Turns a natural-language request into schema-validated, risk-gated calls '
        'against a mock SaaS admin API. Plans the call sequence from the OpenAPI '
        'schema, validates parameters before sending, and dry-runs anything that '
        'writes.'
        '\n\n**Try it:** `POST /v1/assistant/workflows` with a request like "move the '
        'Acme order to express shipping".'
    ),
    version="1.0.0",
)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

app.include_router(business_router)
app.include_router(assistant_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
