"""Web search tool: an offline stub over a small fixed mock index, so the
sandbox is fully demoable without any external API or key.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.core.models import ToolSpec

_MOCK_INDEX: list[dict[str, str]] = [
    {
        "title": "Resetting your password",
        "url": "https://docs.example.com/account/password-reset",
        "snippet": "Use the account settings page to reset your password or request a reset link.",
    },
    {
        "title": "Pricing plans overview",
        "url": "https://docs.example.com/billing/plans",
        "snippet": "Starter, Pro, and Enterprise plans, with details on refunds and proration.",
    },
    {
        "title": "API rate limits",
        "url": "https://docs.example.com/api/rate-limits",
        "snippet": "Default API rate limit is 60 requests per minute per API key.",
    },
    {
        "title": "Troubleshooting failed webhooks",
        "url": "https://docs.example.com/webhooks/troubleshooting",
        "snippet": "Common causes of webhook delivery failures and how to retry them.",
    },
    {
        "title": "Refund policy",
        "url": "https://docs.example.com/billing/refunds",
        "snippet": "Annual plan refunds are prorated; monthly refunds apply within 14 days of charge.",
    },
]


class WebSearchArgs(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    max_results: int = Field(default=3, ge=1, le=5)


def handle(args: WebSearchArgs) -> dict[str, Any]:
    query_terms = {t for t in args.query.lower().split() if t}
    scored = []
    for doc in _MOCK_INDEX:
        text = f"{doc['title']} {doc['snippet']}".lower()
        score = sum(1 for term in query_terms if term in text)
        if score:
            scored.append((score, doc))
    scored.sort(key=lambda pair: -pair[0])
    results = [doc for _, doc in scored[: args.max_results]]
    return {"query": args.query, "results": results}


SPEC = ToolSpec(
    name="web_search",
    description="Search a mock knowledge base for relevant documentation pages.",
    input_schema=WebSearchArgs.model_json_schema(),
    output_schema={
        "type": "object",
        "properties": {"query": {"type": "string"}, "results": {"type": "array"}},
    },
    allowed_roles=["viewer", "analyst", "operator", "admin"],
    rate_limit_per_minute=60,
    risk_level="low",
    requires_approval=False,
)
