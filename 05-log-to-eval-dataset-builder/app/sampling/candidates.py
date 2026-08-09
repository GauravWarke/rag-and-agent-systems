"""High-value candidate identification.

Combines several signals into one score so the highest-leverage logs
surface first for eval-label generation: how unusual the prompt is
relative to its own cluster, whether the interaction shows quality
problems, whether the feature is high-impact, and whether the log's
cluster is under-represented (poor eval coverage).
"""
from __future__ import annotations

import numpy as np

from app.core.models import HighValueCandidate, LogEntry
from app.sampling.cluster import cluster_assignments


def identify_candidates(
    logs: list[LogEntry],
    high_impact_features: set[str] | None = None,
    covered_cluster_ids: set[int] | None = None,
    k: int | None = None,
    seed: int = 42,
    top_n: int = 20,
) -> list[HighValueCandidate]:
    if not logs:
        return []

    high_impact_features = high_impact_features or set()
    covered_cluster_ids = covered_cluster_ids or set()

    assignments, vectors, k = cluster_assignments(logs, k, seed)
    centroids = {
        c: vectors[assignments == c].mean(axis=0) for c in range(k) if (assignments == c).any()
    }
    cluster_sizes = {c: int((assignments == c).sum()) for c in centroids}

    candidates: list[HighValueCandidate] = []
    for i, log in enumerate(logs):
        cluster_id = int(assignments[i])
        centroid = centroids[cluster_id]
        unusualness = float(np.sum((vectors[i] - centroid) ** 2))

        score = 0.0
        reasons: list[str] = []

        # Unusual prompt: far from its own cluster's centroid.
        if unusualness > 0:
            score += unusualness * 2.0
        if unusualness > 0.15:
            reasons.append("unusual prompt within its cluster")

        # Low-quality output signals.
        if log.user_feedback == "negative":
            score += 3.0
            reasons.append("negative user feedback")
        if log.error:
            score += 4.0
            reasons.append("request errored")
        if log.malformed_output:
            score += 3.0
            reasons.append("malformed output")
        if log.safety_flag:
            score += 5.0
            reasons.append("safety edge case")
        if log.retry_count > 0:
            score += 1.5 * log.retry_count
            reasons.append(f"user retried {log.retry_count}x")

        # High-impact feature.
        if log.feature in high_impact_features:
            score += 2.0
            reasons.append(f"high-impact feature '{log.feature}'")

        # Cluster with poor eval coverage: small cluster, or not yet covered.
        cluster_size = cluster_sizes[cluster_id]
        if cluster_id not in covered_cluster_ids:
            score += 1.5
            reasons.append("cluster has no eval coverage yet")
        elif cluster_size <= max(2, len(logs) // (k * 4 or 1)):
            score += 1.0
            reasons.append("small, under-represented cluster")

        if not reasons:
            reasons.append("baseline candidate")

        candidates.append(
            HighValueCandidate(log_id=log.id, score=round(score, 4), reasons=reasons, cluster_id=cluster_id)
        )

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:top_n]
