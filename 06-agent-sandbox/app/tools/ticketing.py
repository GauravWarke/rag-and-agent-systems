"""Ticket creation tool: a mock write-action API. High risk because it
changes external state, so it always requires human approval.
"""
from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.models import ToolSpec

TicketPriority = Literal["low", "normal", "high", "urgent"]


class TicketCreateArgs(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    priority: TicketPriority = "normal"


def handle(args: TicketCreateArgs) -> dict[str, Any]:
    ticket_id = f"TKT-{uuid.uuid4().hex[:8]}"
    return {
        "ticket_id": ticket_id,
        "status": "created",
        "title": args.title,
        "priority": args.priority,
    }


SPEC = ToolSpec(
    name="ticket_create",
    description="Create a support ticket in the (mock) ticketing system.",
    input_schema=TicketCreateArgs.model_json_schema(),
    output_schema={
        "type": "object",
        "properties": {
            "ticket_id": {"type": "string"},
            "status": {"type": "string"},
            "title": {"type": "string"},
            "priority": {"type": "string"},
        },
    },
    allowed_roles=["operator", "admin"],
    rate_limit_per_minute=20,
    risk_level="high",
    requires_approval=True,
)
