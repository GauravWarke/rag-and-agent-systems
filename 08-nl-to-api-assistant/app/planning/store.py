"""In-memory workflow store so a paused (awaiting-confirmation/-approval)
workflow can be looked up and resumed later.
"""
from __future__ import annotations

from app.planning.models import Workflow


class WorkflowStore:
    def __init__(self) -> None:
        self._workflows: dict[str, Workflow] = {}

    def add(self, workflow: Workflow) -> Workflow:
        self._workflows[workflow.id] = workflow
        return workflow

    def get(self, workflow_id: str) -> Workflow | None:
        return self._workflows.get(workflow_id)

    def all(self) -> list[Workflow]:
        return list(self._workflows.values())
