"""In-memory store of ingested log entries.

A demo-scale store: production would back this with Postgres or DuckDB
(as the README's tech stack suggests), but the query surface — `add`,
`get`, `all`, `by_feature` — would stay the same.
"""
from __future__ import annotations

import uuid

from app.core.models import LogEntry, LogIngestRequest
from app.logs.redaction import redact_text


class LogStore:
    def __init__(self) -> None:
        self._entries: dict[str, LogEntry] = {}

    def add(self, req: LogIngestRequest) -> LogEntry:
        prompt_result = redact_text(req.prompt)
        response_result = redact_text(req.response)
        methods = sorted(set(prompt_result.methods) | set(response_result.methods))
        entry = LogEntry(
            id=str(uuid.uuid4()),
            timestamp=req.timestamp,
            feature=req.feature,
            system_prompt=req.system_prompt,
            prompt=prompt_result.text,
            response=response_result.text,
            model=req.model,
            latency_ms=req.latency_ms,
            input_tokens=req.input_tokens,
            output_tokens=req.output_tokens,
            user_feedback=req.user_feedback,
            retry_count=req.retry_count,
            error=req.error,
            malformed_output=req.malformed_output,
            safety_flag=req.safety_flag,
            redacted=prompt_result.redacted or response_result.redacted,
            redaction_methods=methods,
        )
        self._entries[entry.id] = entry
        return entry

    def add_entry(self, entry: LogEntry) -> LogEntry:
        """Insert an already-built LogEntry (e.g. synthetic seed data) as-is."""
        self._entries[entry.id] = entry
        return entry

    def get(self, log_id: str) -> LogEntry | None:
        return self._entries.get(log_id)

    def all(self) -> list[LogEntry]:
        return list(self._entries.values())

    def by_feature(self, feature: str) -> list[LogEntry]:
        return [e for e in self._entries.values() if e.feature == feature]

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)
