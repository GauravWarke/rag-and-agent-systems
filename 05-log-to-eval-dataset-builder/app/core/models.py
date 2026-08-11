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

# Rough difficulty tier derived from the source log's risk signals and the
# label's own confidence — used to slice dataset health and eval-run reports.
Difficulty = Literal["easy", "medium", "hard"]

# Lifecycle status of an eval case in the growing dataset, separate from the
# dedup outcome (`CandidateStatus`) recorded at generation time. "draft"
# means it's sitting in the human review queue; "approved"/"rejected" are
# terminal review outcomes; "deprecated" is for cases later superseded.
ReviewStatus = Literal["draft", "approved", "rejected", "deprecated"]


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
    review_status: ReviewStatus = "draft"
    tags: list[str] = Field(default_factory=list)
    difficulty: Difficulty = "medium"
    cluster_id: int | None = None
    created_at: datetime


class GenerateLabelsRequest(BaseModel):
    log_ids: list[str] = Field(min_length=1, max_length=200)


class GenerateLabelsResponse(BaseModel):
    generated: list[EvalCandidate]
    accepted: int
    rejected_duplicates: int


class ReviewQueueItem(BaseModel):
    """One pending review: the candidate, its source interaction, and the
    already-approved cases it most resembles, so a reviewer can spot
    near-duplicates or inconsistent labeling before deciding."""

    candidate: EvalCandidate
    log: LogEntry
    similar_cases: list[EvalCandidate] = Field(default_factory=list)


ReviewAction = Literal["approve", "edit", "reject", "deprecate"]


class ReviewEditFields(BaseModel):
    """Editable label fields. Only used when action == 'edit'; unset fields are left unchanged."""

    eval_type: EvalType | None = None
    expected_behavior: str | None = Field(default=None, max_length=4000)
    key_assertions: list[str] | None = None
    forbidden_assertions: list[str] | None = None
    rubric: str | None = Field(default=None, max_length=4000)


class ReviewDecisionRequest(BaseModel):
    candidate_id: str
    action: ReviewAction
    reviewer: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=1000)
    edits: ReviewEditFields | None = None


class FieldChange(BaseModel):
    field: str
    old_value: str | None
    new_value: str | None


class ReviewEditLogEntry(BaseModel):
    id: str
    candidate_id: str
    reviewer: str
    action: ReviewAction
    reason: str
    changed_fields: list[FieldChange] = Field(default_factory=list)
    timestamp: datetime


class ReviewDecisionResponse(BaseModel):
    candidate: EvalCandidate
    edit_log: ReviewEditLogEntry


class DeprecateRequest(BaseModel):
    candidate_id: str
    reviewer: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=1000)


class EvalCaseResult(BaseModel):
    """Outcome of running one approved eval case against a model endpoint."""

    candidate_id: str
    eval_type: EvalType
    passed: bool
    actual_response: str
    explanation: str


class EvalRunSummary(BaseModel):
    """One nightly-eval-runner execution over the current approved dataset,
    compared against the immediately preceding run so regressions surface
    without having to diff two full reports by hand."""

    run_id: str
    timestamp: datetime
    model: str
    total_cases: int
    passed: int
    failed: int
    pass_rate: float
    pass_rate_delta: float | None = None
    newly_failing: list[str] = Field(default_factory=list)
    newly_passing: list[str] = Field(default_factory=list)
    results: list[EvalCaseResult] = Field(default_factory=list)


class DatasetHealth(BaseModel):
    """Snapshot of the growing eval dataset's size, composition, and
    review coverage — the numbers a reviewer or CI gate would check before
    trusting the dataset."""

    total_cases: int
    by_eval_type: dict[str, int]
    by_difficulty: dict[str, int]
    by_review_status: dict[str, int]
    auto_labeled_pct: float
    human_reviewed_pct: float
    avg_case_age_days: float
    oldest_case_at: datetime | None
    newest_case_at: datetime | None
