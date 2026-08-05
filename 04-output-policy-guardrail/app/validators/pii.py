"""PII detection: emails, phone numbers, physical addresses, API keys,
credit-card-like numbers, and a naive named-entity heuristic.

This is a deliberately dependency-free, offline, keyless implementation
(regex + a Luhn check) — a production system would swap this for
Presidio or a hosted PII API, but the detection contract (type, span,
confidence) stays the same either way.
"""
from __future__ import annotations

import re

from app.core.models import Finding
from app.policies.store import Policy

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b")
ADDRESS_RE = re.compile(
    r"\b\d{1,5}\s+[A-Za-z0-9.'\s]{1,40}?\s"
    r"(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way)\b\.?",
    re.IGNORECASE,
)
API_KEY_RE = re.compile(
    r"\b(?:sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|(?:api|secret)[_-]?key[_-]?[:=]\s*[A-Za-z0-9/_+.-]{16,})\b",
    re.IGNORECASE,
)
CREDIT_CARD_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")
# Naive: two consecutive capitalized words not at the very start of the text.
NAME_RE = re.compile(r"(?<!^)(?<=[a-z.!?]\s)([A-Z][a-z]+ [A-Z][a-z]+)\b")

# type -> (regex, base confidence)
_DETECTORS: list[tuple[str, re.Pattern[str], float]] = [
    ("email", EMAIL_RE, 0.99),
    ("phone", PHONE_RE, 0.85),
    ("address", ADDRESS_RE, 0.7),
    ("api_key", API_KEY_RE, 0.9),
    ("credit_card", CREDIT_CARD_RE, 0.6),
    ("name", NAME_RE, 0.4),
]


def _luhn_valid(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def detect_pii(text: str, allowed_types: set[str] | None = None) -> list[tuple[str, str, float]]:
    """Return (pii_type, matched_span, confidence) for each hit not in `allowed_types`."""
    allowed = allowed_types or set()
    hits: list[tuple[str, str, float]] = []
    for pii_type, pattern, confidence in _DETECTORS:
        if pii_type in allowed:
            continue
        for match in pattern.finditer(text):
            span = match.group(0)
            if pii_type == "credit_card":
                digits = re.sub(r"[ -]", "", span)
                if not (13 <= len(digits) <= 19 and _luhn_valid(digits)):
                    continue
            hits.append((pii_type, span, confidence))
    return hits


def build_pii_findings(text: str, policy: Policy, allowed_types: list[str] | None = None) -> list[Finding]:
    hits = detect_pii(text, set(allowed_types or []))
    return [
        Finding(
            policy_id=policy.id,
            category=policy.category,
            severity=policy.severity,
            detector="deterministic",
            confidence=confidence,
            evidence=span,
            message=f"Detected possible {pii_type.replace('_', ' ')} in output.",
            recommended_action=policy.recommended_action,
        )
        for pii_type, span, confidence in hits
    ]
