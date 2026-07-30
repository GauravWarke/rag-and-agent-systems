"""Response contract for the AI feature under test (Phase 1, step 3).

The feature turns a messy customer note into a clean, structured CRM
summary. A prompt that returns fluent prose but breaks this schema fails
the release gate before any quality scoring even runs.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Sentiment(str, Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"
    frustrated = "frustrated"


class Urgency(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class NoteSummary(BaseModel):
    """The structured output every prompt version must produce."""

    summary: str = Field(min_length=1, max_length=600)
    sentiment: Sentiment
    next_action: str = Field(min_length=1, max_length=200)
    urgency: Urgency
    confidence: float = Field(ge=0.0, le=1.0)


class SummarizeRequest(BaseModel):
    note: str = Field(min_length=1, max_length=4000)
    prompt_version: str | None = None


class GenerationMeta(BaseModel):
    prompt_name: str
    prompt_version: str
    model: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cost_usd: float
    error: str | None = None


class SummarizeResponse(BaseModel):
    result: NoteSummary
    meta: GenerationMeta
