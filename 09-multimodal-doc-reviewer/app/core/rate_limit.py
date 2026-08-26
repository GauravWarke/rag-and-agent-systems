"""Simple in-memory fixed-window rate limiter for public endpoints.

Good enough for a single-process demo service. A production deployment
behind multiple workers would back this with Redis instead.
"""
from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request

from app.core.config import settings


class RateLimiter:
    def __init__(self, requests_per_minute: int) -> None:
        self.requests_per_minute = requests_per_minute
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        window_start = now - 60.0
        hits = [t for t in self._hits[key] if t > window_start]
        if len(hits) >= self.requests_per_minute:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True

    def clear(self) -> None:
        self._hits.clear()


limiter = RateLimiter(settings.rate_limit_per_minute)


def enforce_rate_limit(request: Request) -> None:
    client_key = request.client.host if request.client else "unknown"
    if not limiter.allow(client_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
