"""Shared models for schema-aware planning: parsed endpoint specs, the
structured call plan the planner proposes, parameter validation results,
and the workflow/task state that tracks a request through dry-run and
confirmation.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

RiskLevel = Literal["read_only", "low_risk_write", "high_risk_write"]


class EndpointParam(BaseModel):
    name: str
    location: Literal["path", "query", "body"]
    required: bool
    param_schema: dict[str, Any] = Field(default_factory=dict)


class EndpointSpec(BaseModel):
    """One endpoint extracted from the OpenAPI schema, enriched with the
    risk/role metadata the business API attaches as OpenAPI extensions.
    """

    operation_id: str
    method: str
    path: str
    summary: str
    description: str
    parameters: list[EndpointParam] = Field(default_factory=list)
    request_body_schema: dict[str, Any] | None = None
    response_schema: dict[str, Any] | None = None
    risk_level: RiskLevel
    required_roles: list[str] = Field(default_factory=list)


class CallPlan(BaseModel):
    """A structured, LLM- or heuristic-proposed call: which endpoint, with
    which parameters, and why — nothing here executes until it has been
    validated and cleared by risk-based gating.
    """

    operation_id: str | None
    method: str | None
    path: str | None
    parameters: dict[str, Any] = Field(default_factory=dict)
    reason: str
    expected_result: str
    requires_confirmation: bool
    risk_level: RiskLevel | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)


class ValidationIssue(BaseModel):
    field: str
    message: str


class ValidationResult(BaseModel):
    valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    filled_parameters: dict[str, Any] = Field(default_factory=dict)


# --- Workflow (dry-run / confirmation / execution) -------------------------

WorkflowStatus = Literal[
    "completed", "denied", "invalid", "failed", "awaiting_confirmation", "awaiting_approval", "rejected"
]


class WorkflowStep(BaseModel):
    node: str
    detail: str
    timestamp: datetime


class Workflow(BaseModel):
    id: str
    user_id: str
    request: str
    status: WorkflowStatus
    plan: CallPlan | None = None
    validation: ValidationResult | None = None
    dry_run_preview: str | None = None
    result: Any | None = None
    error: str | None = None
    steps: list[WorkflowStep] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class CreateWorkflowRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    request: str = Field(min_length=1, max_length=2000)


ResumeDecision = Literal["approve", "reject"]


class ResumeWorkflowRequest(BaseModel):
    decision: ResumeDecision
    reviewer: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=500)
