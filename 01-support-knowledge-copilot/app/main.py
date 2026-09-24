"""Support Knowledge Copilot API.

Endpoints:
  GET  /health   readiness probe
  POST /ask      answer a support question with verified citations

Deployment note: the retriever and the rate limiter are module-level singletons,
so this service assumes a SINGLE worker process. Running it with `--workers N`
gives you N independent indexes and N independent rate-limit counters (making
the effective limit N x the configured value). Scale with replicas behind a
shared limiter instead, or move both into a shared store first.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.models import AskRequest, AskResponse
from app.core.rate_limit import RateLimiter
from app.generation.answer import generate
from app.ingestion.loader import load_sample_corpus
from app.retrieval.hybrid import HybridRetriever

_retriever = HybridRetriever()
_limiter = RateLimiter(settings.rate_limit_per_minute, max_keys=settings.rate_limit_max_clients)

# Routes that serve the interactive API explorer. Swagger UI and ReDoc pull
# their JS/CSS from a CDN, so the strict API CSP below would render them blank.
_DOCS_PATHS = frozenset({"/", "/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"})

# Strict policy for everything that returns JSON: this API never serves HTML,
# so nothing needs to load.
_API_CSP = "default-src 'none'; frame-ancestors 'none'"

# Narrow relaxation for the docs pages only.
# Hosts come from FastAPI's own Swagger UI / ReDoc templates; a test asserts
# every external host those pages reference is listed here, so a FastAPI
# upgrade that moves an asset fails CI instead of silently blanking /docs.
_DOCS_CSP = (
    "default-src 'none'; "
    "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com 'unsafe-inline'; "
    "img-src 'self' data: https://fastapi.tiangolo.com https://cdn.redoc.ly; "
    "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com; "
    "worker-src 'self' blob:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)

# How many reverse proxies sit in front of this app. 0 means "trust the socket
# peer" -- correct for local runs and anything exposed directly. Set it to the
# real hop count when deploying behind a load balancer, otherwise every caller
# shares the proxy's IP and the rate limiter becomes a single global throttle.
# Never trust X-Forwarded-For unconditionally: it is client-controlled, so a
# caller could rotate the header and bypass the limiter entirely.
_TRUSTED_PROXY_HOPS: int = settings.trusted_proxy_hops


def _client_key(request: Request) -> str:
    """Best-effort caller identity for rate limiting.

    With `_TRUSTED_PROXY_HOPS = n`, the n-th entry from the right of
    X-Forwarded-For is the address our own infrastructure appended, so it is the
    last one a client could not have forged.
    """
    peer = request.client.host if request.client else "unknown"
    if _TRUSTED_PROXY_HOPS <= 0:
        return peer

    forwarded = request.headers.get("x-forwarded-for", "")
    hops = [part.strip() for part in forwarded.split(",") if part.strip()]
    if len(hops) >= _TRUSTED_PROXY_HOPS:
        return hops[-_TRUSTED_PROXY_HOPS]
    return peer


@asynccontextmanager
async def lifespan(app: FastAPI):
    _retriever.index(load_sample_corpus())
    yield


app = FastAPI(
    title="Support Knowledge Copilot",
    description=(
        "Answers questions from internal documentation and shows which passage "
        "supports each claim. Hybrid retrieval (dense + BM25, fused with Reciprocal "
        "Rank Fusion), citations verified against source text, and a confidence "
        "score. Returns 'I could not find this in the docs' rather than guessing."
        "\n\n**Try it:** expand `POST /ask`, click *Try it out*, and send a question."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    is_docs = request.url.path in _DOCS_PATHS
    response.headers["Content-Security-Policy"] = _DOCS_CSP if is_docs else _API_CSP
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, request: Request) -> AskResponse:
    if not _limiter.allow(_client_key(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")

    retrieved = _retriever.retrieve(req.question, strategy=req.strategy, access_level=req.access_level)
    return generate(req.question, retrieved)
