"""Alert delivery for freshness/drift signals.

`NullAlertClient` is the offline default: it records alerts instead of
calling out to a real channel, so the pipeline is fully testable without
network access. Configure `SLACK_WEBHOOK_URL` to swap in
`SlackAlertClient`, which posts to a Slack incoming webhook.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import httpx


class AlertClient(ABC):
    name: str

    @abstractmethod
    def send(self, message: str) -> bool:
        """Deliver one alert message. Returns True if it was delivered."""


class NullAlertClient(AlertClient):
    """Offline default: records alerts locally instead of paging anyone."""

    name = "log"

    def __init__(self) -> None:
        self.sent: list[str] = []

    def send(self, message: str) -> bool:
        self.sent.append(message)
        return True


class SlackAlertClient(AlertClient):
    """Requires `SLACK_WEBHOOK_URL`. Posts one message per alert to a Slack
    incoming webhook. Not exercised by the test suite (offline-by-default
    convention) — falls back to `NullAlertClient` when no webhook is
    configured.
    """

    name = "slack"

    def __init__(self, webhook_url: str, timeout: float = 10.0) -> None:
        self._webhook_url = webhook_url
        self._timeout = timeout

    def send(self, message: str) -> bool:
        if not self._webhook_url:
            raise RuntimeError("SLACK_WEBHOOK_URL is not configured")
        response = httpx.post(self._webhook_url, json={"text": message}, timeout=self._timeout)
        response.raise_for_status()
        return True
