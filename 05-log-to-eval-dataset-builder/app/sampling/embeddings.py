"""Embedding provider abstraction.

The default `stub` embedder is deterministic and offline (hashed
bag-of-words projected to a fixed dimension), matching the pattern used
across the other projects in this repo. It lets clustering, diversity
sampling, and dedup all run and be tested without API keys.
"""
from __future__ import annotations

import hashlib
import math
import re

import numpy as np

_DIM = 128
_TOKEN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def embed(text: str) -> np.ndarray:
    vec = np.zeros(_DIM, dtype=np.float64)
    for tok in _tokenize(text):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        vec[h % _DIM] += 1.0
    norm = math.sqrt(float(np.dot(vec, vec))) or 1.0
    return vec / norm


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
    return float(np.dot(a, b) / denom)
