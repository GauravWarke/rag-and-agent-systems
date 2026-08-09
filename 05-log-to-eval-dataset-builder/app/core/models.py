"""Shared Pydantic models: the unified log schema and sampling/cluster
request-response shapes used across the ingestion, sampling, and
labeling modules.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Feedback = Literal["positive", "negative", "none"]


class LogEntry(BaseModel):
    """One production-like LLM interaction.

    Captures everything downstream sampling, clustering, and labeling
    need: the interaction itself, quality signals (feedback, retries,
    errors), and enough metadata to slice by feature over time.
    """

    id: str
    timestamp: datetime
    feature: str
    system_prompt: str | None = None
    prompt: str
    response: str
    model: str
    latency_ms: float = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    user_feedback: Feedback = "none"
    retry_count: int = Field(default=0, ge=0)
    error: bool = False
    malformed_output: bool = False
    safety_flag: bool = False
    redacted: bool = False
    redaction_methods: list[str] = Field(default_factory=list)


class LogIngestRequest(BaseModel):
    """Body for POST /v1/logs — same shape as LogEntry minus server-assigned id."""

    timestamp: datetime
    feature: str = Field(min_length=1, max_length=128)
    system_prompt: str | None = Field(default=None, max_length=8000)
    prompt: str = Field(min_length=1, max_length=8000)
    response: str = Field(min_length=0, max_length=16000)
    model: str = Field(min_length=1, max_length=128)
    latency_ms: float = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    user_feedback: Feedback = "none"
    retry_count: int = Field(default=0, ge=0)
    error: bool = False
    malformed_output: bool = False
    safety_flag: bool = False


class SeedLogsRequest(BaseModel):
    n: int = Field(default=1000, ge=1, le=20000)
    seed: int = Field(default=42, description="RNG seed for reproducible synthetic logs")


class SeedLogsResponse(BaseModel):
    created: int
    total_logs: int


SamplingMode = Literal["random", "failure_biased", "diversity"]


class SampleRequest(BaseModel):
    mode: SamplingMode
    n: int = Field(default=20, ge=1, le=1000)
    feature: str | None = None
    seed: int = Field(default=42)


class ClusterInfo(BaseModel):
    cluster_id: int
    label: str
    size: int
    representative_prompt: str
    example_log_ids: list[str]


class HighValueCandidate(BaseModel):
    log_id: str
    score: float
    reasons: list[str]
    cluster_id: int | None = None


EvalType = Literal["golden_answer", "rubric", "expected_refusal"]
CandidateStatus = Literal["accepted", "rejected_duplicate"]


class ProposedLabel(BaseModel):
    eval_type: EvalType
    expected_behavior: str
    key_assertions: list[str] = Field(default_factory=list)
    forbidden_assertions: list[str] = Field(default_factory=list)
    rubric: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class EvalCandidate(BaseModel):
    id: str
    log_id: str
    feature: str
    input: str
    eval_type: EvalType
    expected_behavior: str
    key_assertions: list[str] = Field(default_factory=list)
    forbidden_assertions: list[str] = Field(default_factory=list)
    rubric: str | None = None
    confidence: float
    status: CandidateStatus
    reason: str
    duplicate_of: str | None = None


class GenerateLabelsRequest(BaseModel):
    log_ids: list[str] = Field(min_length=1, max_length=200)


class GenerateLabelsResponse(BaseModel):
    generated: list[EvalCandidate]
    accepted: int
    rejected_duplicates: int
