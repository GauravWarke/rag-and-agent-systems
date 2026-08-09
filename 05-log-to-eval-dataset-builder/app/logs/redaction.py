"""Deterministic PII redaction rules applied to log text before storage.

Rules run in a fixed order and each records its own method name so a
log entry can report exactly which redactions fired. Kept regex-based
and offline: no external PII-detection service required.
"""
from __future__ import annotations

import re

from pydantic import BaseModel

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)")
# Common API-key-shaped secrets: OpenAI-style sk-..., AWS access keys, generic
# 32+ char hex/base64-ish tokens after "key=" / "token=" / "secret=".
_SECRET_RE = re.compile(
    r"\b(?:sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|(?:key|token|secret)[=:]\s*[A-Za-z0-9/_+.-]{12,})\b",
    re.IGNORECASE,
)
# A small deterministic name list keeps redaction testable without a full
# NER model. Falls back to a generic "First Last" capitalized-pair pattern
# for names not on the list.
_KNOWN_NAMES = {"John Smith", "Jane Doe", "Maria Garcia", "Wei Chen", "Priya Patel", "Alex Johnson"}
_NAME_PAIR_RE = re.compile(r"\b(Dear|Hi|Hello|Regards|From|Best),?\s+([A-Z][a-z]+\s[A-Z][a-z]+)")


class RedactionResult(BaseModel):
    text: str
    redacted: bool
    methods: list[str]


def redact_text(text: str) -> RedactionResult:
    methods: list[str] = []
    out = text

    if _EMAIL_RE.search(out):
        out = _EMAIL_RE.sub("[REDACTED_EMAIL]", out)
        methods.append("email")

    if _PHONE_RE.search(out):
        out = _PHONE_RE.sub("[REDACTED_PHONE]", out)
        methods.append("phone")

    if _SECRET_RE.search(out):
        out = _SECRET_RE.sub("[REDACTED_SECRET]", out)
        methods.append("secret")

    for name in _KNOWN_NAMES:
        if name in out:
            out = out.replace(name, "[REDACTED_NAME]")
            if "name" not in methods:
                methods.append("name")

    def _sub_name_pair(match: re.Match[str]) -> str:
        return f"{match.group(1)}, [REDACTED_NAME]"

    if _NAME_PAIR_RE.search(out):
        out = _NAME_PAIR_RE.sub(_sub_name_pair, out)
        if "name" not in methods:
            methods.append("name")

    return RedactionResult(text=out, redacted=bool(methods), methods=methods)
