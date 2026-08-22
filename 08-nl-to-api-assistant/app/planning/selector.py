"""Endpoint selector: narrows the full parsed OpenAPI endpoint list down to
the handful most relevant to a natural-language request, using keyword
overlap. Kept dependency-free (no embeddings) to stay offline-runnable by
default; a real deployment could swap this for an embedding-based lookup
without changing the planner's interface.
"""
from __future__ import annotations

import re

from app.planning.models import EndpointSpec

_WORD = re.compile(r"[a-z]+")


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def _endpoint_tokens(endpoint: EndpointSpec) -> set[str]:
    path_words = endpoint.path.replace("/", " ").replace("{", "").replace("}", "")
    text = " ".join([endpoint.operation_id.replace("_", " "), endpoint.summary, endpoint.description, path_words])
    return _tokens(text)


def select_endpoints(request: str, endpoints: list[EndpointSpec], top_k: int = 3) -> list[EndpointSpec]:
    """Return up to `top_k` endpoints whose name/summary/description/path
    share at least one word with the request, most-overlap first. Returns
    an empty list when nothing overlaps at all — a clear "no relevant
    endpoint" signal instead of a low-confidence guess.
    """
    request_tokens = _tokens(request)
    scored = [(endpoint, len(request_tokens & _endpoint_tokens(endpoint))) for endpoint in endpoints]
    scored = [pair for pair in scored if pair[1] > 0]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return [endpoint for endpoint, _ in scored[:top_k]]
