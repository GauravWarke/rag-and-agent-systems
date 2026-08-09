from app.logs.redaction import redact_text


def test_redacts_email():
    result = redact_text("Contact me at jane.doe@example.com for details.")
    assert "jane.doe@example.com" not in result.text
    assert "[REDACTED_EMAIL]" in result.text
    assert result.redacted is True
    assert "email" in result.methods


def test_redacts_phone():
    result = redact_text("Call me at 555-201-3344 tomorrow.")
    assert "555-201-3344" not in result.text
    assert "[REDACTED_PHONE]" in result.text
    assert "phone" in result.methods


def test_redacts_secret():
    result = redact_text("Here is my key: sk-abcdefghijklmnopqrstuvwx")
    assert "sk-abcdefghijklmnopqrstuvwx" not in result.text
    assert "[REDACTED_SECRET]" in result.text
    assert "secret" in result.methods


def test_redacts_known_name():
    result = redact_text("Customer John Smith says the export button is broken.")
    assert "John Smith" not in result.text
    assert "name" in result.methods


def test_redacts_name_after_greeting():
    result = redact_text("Dear Maria Garcia, thanks for reaching out.")
    assert "Maria Garcia" not in result.text
    assert "name" in result.methods


def test_no_redaction_needed():
    result = redact_text("The dashboard export button does nothing.")
    assert result.redacted is False
    assert result.methods == []
    assert result.text == "The dashboard export button does nothing."


def test_multiple_redactions_combined():
    result = redact_text("Email jane.doe@example.com or call 555-201-3344.")
    assert set(result.methods) == {"email", "phone"}
