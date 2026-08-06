"""Safe rewrite flows for fixable policy violations.

Only categories with a known-safe, mechanical transformation are
rewritten automatically: PII spans are redacted, malformed/incomplete
JSON is repaired against the feature's expected schema, and
overconfident phrasing is softened. A finding recommending `rewrite`
that doesn't match one of those categories is left unresolved rather
than guessed at — better to say so than to silently mangle text no
rule covers.
"""
from __future__ import annotations

import json
import re

from pydantic import BaseModel

from app.core.models import Finding
from app.validators.schema import TYPE_MAP

_PII_PLACEHOLDER = "[REDACTED]"

# phrase -> hedged replacement, matched case-insensitively. Longer/more
# specific phrases are listed before the general ones they contain so
# the specific replacement wins.
_OVERCONFIDENT_PHRASES: list[tuple[str, str]] = [
    ("you definitely have", "you may have"),
    ("you will definitely win", "you may have a strong case, but outcomes vary"),
    ("guaranteed to double", "may change in value"),
    ("no need for a lawyer", "consider consulting a lawyer to be sure"),
    ("just take ibuprofen", "consider over-the-counter pain relief, but consult a doctor if it persists"),
    ("100% certain", "likely"),
    ("always works", "often works"),
    ("never fails", "rarely fails"),
    ("guaranteed", "likely"),
    ("definitely", "likely"),
]

_TYPE_DEFAULTS: dict[str, object] = {"str": "", "int": 0, "float": 0.0, "bool": False, "list": [], "dict": {}}


class RewriteResult(BaseModel):
    text: str
    applied_policy_ids: list[str]
    fully_resolved: bool


def apply_rewrite(output: str, findings: list[Finding], expected_schema: dict[str, str] | None) -> RewriteResult:
    """Apply every fixable `rewrite` finding to `output` and return the result.

    Findings recommending an action other than `rewrite` are ignored
    here — they've already been reflected in `warnings` or a stronger
    action upstream.
    """
    text = output
    applied: list[str] = []
    fully_resolved = True

    for finding in findings:
        if finding.recommended_action != "rewrite":
            continue
        if finding.category == "pii":
            if finding.evidence and finding.evidence in text:
                text = text.replace(finding.evidence, _PII_PLACEHOLDER)
                applied.append(finding.policy_id)
            else:
                fully_resolved = False
        elif finding.category == "structural":
            repaired = _repair_json(text, expected_schema)
            if repaired is not None:
                text = repaired
                applied.append(finding.policy_id)
            else:
                fully_resolved = False
        elif finding.category == "overconfidence":
            softened, changed = _soften(text)
            if changed:
                text = softened
                applied.append(finding.policy_id)
            else:
                fully_resolved = False
        else:
            fully_resolved = False

    return RewriteResult(text=text, applied_policy_ids=applied, fully_resolved=fully_resolved)


def _soften(text: str) -> tuple[str, bool]:
    changed = False
    result = text
    for phrase, replacement in _OVERCONFIDENT_PHRASES:
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        if pattern.search(result):
            result = pattern.sub(replacement, result)
            changed = True
    return result, changed


def _repair_json(text: str, expected_schema: dict[str, str] | None) -> str | None:
    """Best-effort JSON repair: fill missing fields and coerce
    wrong-typed fields to a safe default of the expected type.

    Returns None when `text` isn't valid JSON at all — that's not
    something a mechanical rewrite can safely fix.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    if not expected_schema:
        return text

    for field, type_name in expected_schema.items():
        py_type = TYPE_MAP.get(type_name)
        if field not in data or (py_type is not None and not isinstance(data[field], py_type)):
            data[field] = _TYPE_DEFAULTS.get(type_name)
    return json.dumps(data)
