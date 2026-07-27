"""Golden Q&A set (Phase 5, step 1).

Hand-written questions tied to the bundled sample corpus, covering simple
lookups, multi-doc questions, ambiguous questions, outdated-document traps
(false-premise questions), and questions with no answer in the corpus. The
retrieval/answer eval runner (a later Phase 5 step) scores the pipeline
against this set.
"""
from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel

_DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "golden_qa.jsonl"


class GoldenCategory(str, Enum):
    simple_lookup = "simple_lookup"
    multi_doc = "multi_doc"
    ambiguous = "ambiguous"
    outdated_trap = "outdated_trap"
    no_answer = "no_answer"


class GoldenQA(BaseModel):
    id: str
    question: str
    category: GoldenCategory
    expected_sources: list[str] = []
    expected_answer_contains: list[str] = []
    expect_no_answer: bool = False
    notes: str = ""


def load_golden_set(path: Path | None = None) -> list[GoldenQA]:
    """Load and validate the golden Q&A set from a JSONL file."""
    target = path or _DEFAULT_PATH
    cases = []
    with target.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            cases.append(GoldenQA.model_validate(json.loads(line)))
    return cases
