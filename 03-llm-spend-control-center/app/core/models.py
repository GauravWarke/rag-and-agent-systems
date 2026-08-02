"""Request/response contracts for the unified LLM gateway.

`GatewayRequest` is the one shape every caller (team/feature) sends
regardless of which provider or model eventually serves it.
`GatewayResponse` is the one shape every caller gets back regardless of
which provider produced it — providers each return their own raw
response shape, and adapters normalize it into this schema.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant"]
Priority = Literal["low", "normal", "high"]
BudgetStatus = Literal["ok", "warning", "blocked"]


class ChatMessage(BaseModel):
    role: Role
    content: str = Field(min_length=1, max_length=8000)


class GatewayRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=50)
    team_id: str = Field(min_length=1, max_length=64)
    feature: str = Field(min_length=1, max_length=64)
    priority: Priority = "normal"
    model: str | None = None
    max_tokens: int = Field(default=512, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    risk_tags: list[str] = Field(default_factory=list, max_length=10)
    override_budget_block: bool = False


class GatewayResponse(BaseModel):
    request_id: str
    output: str
    provider: str
    model_used: str
    routing_tier: int | None = None
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    budget_status: BudgetStatus = "ok"
    warnings: list[str] = Field(default_factory=list)
    escalated: bool = False
    escalation_reason: str | None = None
