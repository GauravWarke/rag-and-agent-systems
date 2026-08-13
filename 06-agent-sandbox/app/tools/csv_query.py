"""CSV query tool over a small embedded customer-accounts dataset.

Medium risk: it surfaces real business data (plan, MRR, status), so the
sandbox requires confirmation before running it (see app/permissions).
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.core.models import ToolSpec

_ROWS: list[dict[str, Any]] = [
    {"customer_id": "C-1001", "plan": "pro", "status": "active", "mrr": 49},
    {"customer_id": "C-1002", "plan": "starter", "status": "active", "mrr": 9},
    {"customer_id": "C-1003", "plan": "enterprise", "status": "active", "mrr": 499},
    {"customer_id": "C-1004", "plan": "pro", "status": "past_due", "mrr": 49},
    {"customer_id": "C-1005", "plan": "starter", "status": "cancelled", "mrr": 0},
    {"customer_id": "C-1006", "plan": "pro", "status": "active", "mrr": 49},
]
_COLUMNS = {"customer_id", "plan", "status", "mrr"}


class CsvQueryArgs(BaseModel):
    column: str = Field(min_length=1, max_length=64)
    value: str = Field(min_length=1, max_length=128)
    limit: int = Field(default=10, ge=1, le=100)


def handle(args: CsvQueryArgs) -> dict[str, Any]:
    if args.column not in _COLUMNS:
        raise ValueError(f"Unknown column {args.column!r}. Valid columns: {sorted(_COLUMNS)}")
    matches = [row for row in _ROWS if str(row[args.column]).lower() == args.value.lower()]
    return {
        "column": args.column,
        "value": args.value,
        "matches": matches[: args.limit],
        "total_matches": len(matches),
    }


SPEC = ToolSpec(
    name="csv_query",
    description="Query the customer-accounts dataset by exact column value.",
    input_schema=CsvQueryArgs.model_json_schema(),
    output_schema={
        "type": "object",
        "properties": {
            "column": {"type": "string"},
            "value": {"type": "string"},
            "matches": {"type": "array"},
            "total_matches": {"type": "integer"},
        },
    },
    allowed_roles=["analyst", "operator", "admin"],
    rate_limit_per_minute=30,
    risk_level="medium",
    requires_approval=False,
    fallback_tool="web_search",
)
