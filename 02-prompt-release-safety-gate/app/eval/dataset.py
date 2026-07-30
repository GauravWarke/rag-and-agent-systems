"""Golden test set (Phase 2): hand-written messy customer notes with
expected structured CRM summary fields, tied to stable IDs and versioned
via `data/CHANGELOG.md`.
"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

_DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "golden_test_set.jsonl"


class ExpectedFields(BaseModel):
    sentiment: str
    urgency: str
    next_action_keywords: list[str] = Field(default_factory=list)
    summary_keywords: list[str] = Field(default_factory=list)


class GoldenCase(BaseModel):
    id: str
    note: str
    category: str
    difficulty: str
    risk_area: str
    why_this_case_exists: str
    expected: ExpectedFields


def load_golden_set(path: Path | None = None) -> list[GoldenCase]:
    """Load and validate the golden test set from a JSONL file."""
    target = path or _DEFAULT_PATH
    cases = []
    with target.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            cases.append(GoldenCase.model_validate(json.loads(line)))
    return cases
