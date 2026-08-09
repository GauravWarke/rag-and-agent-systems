from datetime import datetime, timezone

from app.core.models import LogIngestRequest
from app.logs.store import LogStore


def _req(**overrides) -> LogIngestRequest:
    defaults = {
        "timestamp": datetime.now(timezone.utc),
        "feature": "crm_note_summary",
        "prompt": "Customer says the export button is broken.",
        "response": "Summary: export button bug reported.",
        "model": "gpt-4o-mini",
        "latency_ms": 200.0,
        "input_tokens": 50,
        "output_tokens": 20,
    }
    defaults.update(overrides)
    return LogIngestRequest(**defaults)


def test_add_assigns_id_and_stores():
    store = LogStore()
    entry = store.add(_req())
    assert entry.id
    assert store.get(entry.id) == entry
    assert len(store) == 1


def test_add_redacts_pii_in_prompt_and_response():
    store = LogStore()
    entry = store.add(
        _req(prompt="Contact jane.doe@example.com about the issue.", response="Ok, emailing jane.doe@example.com now.")
    )
    assert "jane.doe@example.com" not in entry.prompt
    assert "jane.doe@example.com" not in entry.response
    assert entry.redacted is True
    assert "email" in entry.redaction_methods


def test_by_feature_filters():
    store = LogStore()
    store.add(_req(feature="crm_note_summary"))
    store.add(_req(feature="ticket_triage"))
    assert len(store.by_feature("crm_note_summary")) == 1
    assert len(store.by_feature("ticket_triage")) == 1
    assert len(store.by_feature("unknown")) == 0


def test_get_missing_returns_none():
    store = LogStore()
    assert store.get("does-not-exist") is None
