"""Golden workflow test suite (Phase 5): replays a fixed set of
natural-language requests — clean single calls, low- and high-risk writes,
ambiguous/unmatched requests, requests missing a required field, and
multi-step chains — against the real planning pipeline and checks each one
lands on its expected endpoint plan and workflow status. This is the
regression net for the planner/selector/validator/chain logic: a change
that reroutes or silently "fixes" an unsafe request should break a case
here.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

_GOLDEN_PATH = Path(__file__).resolve().parent.parent / "data" / "golden_workflows.jsonl"


def _load_cases() -> list[dict]:
    with _GOLDEN_PATH.open() as f:
        return [json.loads(line) for line in f if line.strip()]


_CASES = _load_cases()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_golden_set_has_expected_size_and_coverage():
    assert 40 <= len(_CASES) <= 50
    categories = {case["category"] for case in _CASES}
    assert {"read_only", "low_risk_write", "high_risk_write", "ambiguous", "chain"} <= categories
    assert len(_CASES) == len({case["id"] for case in _CASES})


@pytest.mark.parametrize("case", _CASES, ids=[case["id"] for case in _CASES])
def test_golden_workflow_case(client, case):
    response = client.post("/v1/assistant/workflows", json={"user_id": "golden", "request": case["request"]})
    assert response.status_code == 200
    body = response.json()

    assert body["status"] == case["expected_status"], case["notes"]

    if "expected_chain_operation_ids" in case:
        chain = body["chain"] or []
        assert [step["operation_id"] for step in chain] == case["expected_chain_operation_ids"], case["notes"]
    else:
        plan = body["plan"] or {}
        assert plan.get("operation_id") == case.get("expected_operation_id"), case["notes"]
        if "expected_max_confidence" in case:
            assert plan.get("confidence", 1.0) <= case["expected_max_confidence"], case["notes"]
