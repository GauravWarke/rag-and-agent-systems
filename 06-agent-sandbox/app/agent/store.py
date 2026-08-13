"""In-memory task store so a paused (awaiting-confirmation/-approval) task
can be looked up and resumed later.
"""
from __future__ import annotations

from app.core.models import AgentTask


class TaskStore:
    def __init__(self) -> None:
        self._tasks: dict[str, AgentTask] = {}

    def add(self, task: AgentTask) -> AgentTask:
        self._tasks[task.id] = task
        return task

    def get(self, task_id: str) -> AgentTask | None:
        return self._tasks.get(task_id)

    def all(self) -> list[AgentTask]:
        return list(self._tasks.values())
