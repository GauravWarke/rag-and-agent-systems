"""Sampling modes for pulling candidate logs out of the full log store.

- random: unbiased baseline, useful for measuring what "typical" traffic
  looks like.
- failure_biased: over-selects logs with negative feedback, retries,
  errors, malformed output, or safety flags — the traffic most likely
  to expose regressions.
- diversity: greedy farthest-point sampling over prompt embeddings so
  the sample spans many topics instead of clustering around one.
"""
from __future__ import annotations

import numpy as np

from app.core.models import LogEntry
from app.sampling.embeddings import embed


def _failure_weight(log: LogEntry) -> float:
    weight = 1.0
    if log.user_feedback == "negative":
        weight += 3.0
    weight += 2.0 * log.retry_count
    if log.error:
        weight += 5.0
    if log.malformed_output:
        weight += 3.0
    if log.safety_flag:
        weight += 4.0
    return weight


def random_sample(logs: list[LogEntry], n: int, seed: int = 42) -> list[LogEntry]:
    rng = np.random.default_rng(seed)
    if not logs:
        return []
    k = min(n, len(logs))
    idx = rng.choice(len(logs), size=k, replace=False)
    return [logs[i] for i in idx]


def failure_biased_sample(logs: list[LogEntry], n: int, seed: int = 42) -> list[LogEntry]:
    if not logs:
        return []
    rng = np.random.default_rng(seed)
    k = min(n, len(logs))
    weights = np.array([_failure_weight(log) for log in logs], dtype=np.float64)
    probs = weights / weights.sum()
    idx = rng.choice(len(logs), size=k, replace=False, p=probs)
    return [logs[i] for i in idx]


def diversity_sample(logs: list[LogEntry], n: int, seed: int = 42) -> list[LogEntry]:
    if not logs:
        return []
    k = min(n, len(logs))
    vectors = [embed(log.prompt) for log in logs]

    rng = np.random.default_rng(seed)
    first = int(rng.integers(0, len(logs)))
    selected_idx = [first]
    min_dist = np.array([1.0 - float(np.dot(vectors[first], v)) for v in vectors])
    min_dist[first] = -1.0  # never re-select

    while len(selected_idx) < k:
        next_idx = int(np.argmax(min_dist))
        selected_idx.append(next_idx)
        min_dist[next_idx] = -1.0
        for j, v in enumerate(vectors):
            if min_dist[j] < 0:
                continue
            dist = 1.0 - float(np.dot(vectors[next_idx], v))
            min_dist[j] = min(min_dist[j], dist)

    return [logs[i] for i in selected_idx]
