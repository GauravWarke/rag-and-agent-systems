"""Simple in-memory fixed-window rate limiter for public endpoints.

Good enough for a single-process demo service. A production deployment
behind multiple workers would back this with Redis instead.

Memory is bounded: clients whose last hit has aged out of the window are
swept periodically, and if the table is still full the least-recently-seen
client is evicted. Eviction resets that client's count, which is the right
trade-off here -- the alternatives are unbounded growth or refusing every
new client once the table fills.
"""
from __future__ import annotations

import time

_WINDOW_SECONDS = 60.0
_SWEEP_EVERY = 1024


class RateLimiter:
    def __init__(self, requests_per_minute: int, max_keys: int = 10_000) -> None:
        if max_keys < 1:
            raise ValueError("max_keys must be >= 1")
        self.requests_per_minute = requests_per_minute
        self.max_keys = max_keys
        # Insertion-ordered: every hit re-inserts its key at the end, so the
        # first key is always the least recently seen.
        self._hits: dict[str, list[float]] = {}
        self._calls = 0

    def _sweep(self, window_start: float) -> None:
        stale = [k for k, ts in self._hits.items() if not ts or ts[-1] <= window_start]
        for k in stale:
            del self._hits[k]

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        window_start = now - _WINDOW_SECONDS

        self._calls += 1
        if self._calls % _SWEEP_EVERY == 0:
            self._sweep(window_start)

        hits = [t for t in self._hits.pop(key, ()) if t > window_start]

        if len(self._hits) >= self.max_keys:
            self._sweep(window_start)
            while len(self._hits) >= self.max_keys:
                del self._hits[next(iter(self._hits))]

        if len(hits) >= self.requests_per_minute:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True
