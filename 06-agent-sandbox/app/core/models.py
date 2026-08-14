"""Shared domain models: users/roles, the tool registry contract, tool-call
request/response shapes, and the agent workflow's task/step state.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

Role = Literal["viewer", "analyst", "operator", "admin"]
RiskLevel = Literal["low", "medium", "high"]

# Outcome of a permission check for one (user, tool) pair. "allowed" means
# the tool call may execute now; the other statuses all short-circuit
# execution for a distinct reason.
PermissionStatus = Literal[
    "allowed", "denied", "needs_confirmation", "needs_approval", "invalid_input"
]


class User(BaseModel):
    id: str
    role: Role


class ToolSpec(BaseModel):
    """Registry entry for one tool. Every tool call is checked against this
    before anything the model produced is allowed to run.
    """

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    allowed_roles: list[Role]
    rate_limit_per_minute: int
    risk_level: RiskLevel
    requires_approval: bool = False
    # Lower-risk tool to retry with if this one fails during agent execution.
    fallback_tool: str | None = None


class ToolCallRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    tool_name: str = Field(min_length=1, max_length=64)
    arguments: dict[str, Any] = Field(default_factory=dict)
    # Client's acknowledgement for medium-risk tools ("are you sure?").
    confirmed: bool = False
    # Set only by the resume-after-approval path, once a human has actually
    # approved the pending high-risk action out of band.
    human_approved: bool = False


class ToolCallResult(BaseModel):
    tool_name: str
    permission_status: PermissionStatus
    success: bool
    output: Any | None = None
    error: str | None = None
    risk_level: RiskLevel
    latency_ms: float = 0.0


# --- Agent workflow -------------------------------------------------------

NodeName = Literal[
    "intake",
    "plan",
    "tool_selection",
    "permission_check",
    "tool_execution",
    "result_reflection",
    "approval_wait",
    "final_response",
]

TaskStatus = Literal[
    "completed", "denied", "failed", "awaiting_confirmation", "awaiting_approval"
]


class AgentStep(BaseModel):
    node: NodeName
    detail: str
    timestamp: datetime


class PendingAction(BaseModel):
    tool_name: str
    arguments: dict[str, Any]
    risk_level: RiskLevel


class AgentTask(BaseModel):
    id: str
    user_id: str
    request: str
    status: TaskStatus
    steps: list[AgentStep] = Field(default_factory=list)
    pending_action: PendingAction | None = None
    result: ToolCallResult | None = None
    final_response: str | None = None
    created_at: datetime
    updated_at: datetime


class AgentTaskRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    request: str = Field(min_length=1, max_length=2000)


ResumeDecision = Literal["approve", "reject", "modify", "replan"]


class ResumeTaskRequest(BaseModel):
    decision: ResumeDecision
    reviewer: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=500)
    # Required when decision="modify" (the edited arguments to run with);
    # ignored for "reject"/"replan" and optional for "approve".
    modified_arguments: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _modify_requires_arguments(self) -> ResumeTaskRequest:
        if self.decision == "modify" and self.modified_arguments is None:
            raise ValueError("decision='modify' requires modified_arguments.")
        return self


# --- Human approval queue and audit log (Phase 4) --------------------------


class DecisionLog(BaseModel):
    """A structured, queryable record of one human approval decision — who
    decided what, on which task, and why. Kept separate from the free-text
    step appended to `AgentTask.steps` so it can be listed/filtered on its
    own for auditing.
    """

    id: str
    task_id: str
    tool_name: str
    risk_level: RiskLevel
    decision: ResumeDecision
    reviewer: str
    reason: str
    original_arguments: dict[str, Any]
    modified_arguments: dict[str, Any] | None = None
    outcome_status: TaskStatus
    timestamp: datetime


class ApprovalQueueItem(BaseModel):
    """Read-model for the human approval queue: one paused task with enough
    context (proposed action, risk, model reasoning, expected effect) for a
    reviewer to decide without opening the raw task record.
    """

    task_id: str
    user_id: str
    request: str
    status: TaskStatus
    tool_name: str
    arguments: dict[str, Any]
    risk_level: RiskLevel
    reasoning_summary: str
    expected_effect: str
    created_at: datetime
    updated_at: datetime


# --- Observability / tracing (Phase 5) -------------------------------------


class TraceSpan(BaseModel):
    """One entry in a task's timeline, enriched with latency/cost where the
    underlying step is a tool execution.
    """

    index: int
    node: NodeName
    detail: str
    timestamp: datetime
    latency_ms: float | None = None
    cost_usd: float | None = None


class TraceResponse(BaseModel):
    task_id: str
    status: TaskStatus
    spans: list[TraceSpan]
    decisions: list[DecisionLog]
    total_latency_ms: float
    total_cost_usd: float
