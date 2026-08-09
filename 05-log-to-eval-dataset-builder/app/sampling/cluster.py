"""Lightweight k-means clustering over prompt embeddings.

Discovers common prompt categories so candidate selection (Phase 2) and
eval-coverage analysis (Phase 3/5) can reason about "clusters" instead
of raw logs. Pure numpy — no sklearn/HDBSCAN dependency required to
keep the project offline-runnable out of the box.
"""
from __future__ import annotations

import re
from collections import Counter

import numpy as np

from app.core.models import ClusterInfo, LogEntry
from app.sampling.embeddings import embed

_STOPWORDS = {
    "the", "a", "an", "this", "that", "is", "was", "for", "and", "to", "of",
    "in", "on", "please", "customer", "with", "says", "from", "who", "reports",
}
_TOKEN = re.compile(r"[a-z0-9]+")


def _kmeans(vectors: np.ndarray, k: int, seed: int, iterations: int = 25) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = vectors.shape[0]
    init_idx = rng.choice(n, size=k, replace=False)
    centroids = vectors[init_idx].copy()

    assignments = np.full(n, -1, dtype=int)
    for _ in range(iterations):
        # Squared euclidean distance on normalized vectors ranks the same
        # as cosine distance, so this stays consistent with the rest of
        # the module's cosine-similarity based reasoning.
        dists = ((vectors[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        new_assignments = dists.argmin(axis=1)
        converged = np.array_equal(new_assignments, assignments)
        assignments = new_assignments
        if converged:
            break
        for c in range(k):
            members = vectors[assignments == c]
            if len(members) > 0:
                centroids[c] = members.mean(axis=0)
    return assignments


def _cluster_label(prompts: list[str]) -> str:
    counts: Counter[str] = Counter()
    for prompt in prompts:
        tokens = [t for t in _TOKEN.findall(prompt.lower()) if t not in _STOPWORDS and len(t) > 2]
        counts.update(set(tokens))
    top = [tok for tok, _ in counts.most_common(3)]
    return ", ".join(top) if top else "misc"


def cluster_assignments(
    logs: list[LogEntry], k: int | None = None, seed: int = 42
) -> tuple[np.ndarray, np.ndarray, int]:
    """Returns (assignments, embedding_vectors, k) aligned with `logs`."""
    k = k or max(2, min(8, len(logs) // 20 or 1))
    k = min(k, len(logs))
    vectors = np.stack([embed(log.prompt) for log in logs])
    assignments = _kmeans(vectors, k, seed)
    return assignments, vectors, k


def cluster_logs(logs: list[LogEntry], k: int | None = None, seed: int = 42) -> list[ClusterInfo]:
    if not logs:
        return []

    assignments, vectors, k = cluster_assignments(logs, k, seed)

    clusters: list[ClusterInfo] = []
    for c in range(k):
        member_idx = [i for i, a in enumerate(assignments) if a == c]
        if not member_idx:
            continue
        members = [logs[i] for i in member_idx]
        centroid = vectors[member_idx].mean(axis=0)
        # Representative = member closest to the centroid.
        best_i = member_idx[0]
        best_dist = float("inf")
        for i in member_idx:
            dist = float(np.sum((vectors[i] - centroid) ** 2))
            if dist < best_dist:
                best_dist = dist
                best_i = i

        clusters.append(
            ClusterInfo(
                cluster_id=c,
                label=_cluster_label([m.prompt for m in members]),
                size=len(members),
                representative_prompt=logs[best_i].prompt,
                example_log_ids=[m.id for m in members[:5]],
            )
        )

    return clusters
