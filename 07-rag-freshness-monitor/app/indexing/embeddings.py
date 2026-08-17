"""Embedding provider abstraction.

The default `stub` embedder is deterministic and offline (hashed bag-of-words
projected to a fixed dimension). It lets semantic-change scoring and probe
retrieval run and be tested without API keys. Swap `EMBEDDING_MODEL` to a
real provider later.
"""
from __future__ import annotations

import hashlib
import math
import re

from app.core.config import settings

_DIM = 256
_TOKEN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def embed(text: str) -> list[float]:
    if settings.embedding_model != "stub":
        raise NotImplementedError(
            f"Embedding model '{settings.embedding_model}' not wired yet; "
            "use EMBEDDING_MODEL=stub or implement the provider adapter."
        )
    vec = [0.0] * _DIM
    for tok in _tokenize(text):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        vec[h % _DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
