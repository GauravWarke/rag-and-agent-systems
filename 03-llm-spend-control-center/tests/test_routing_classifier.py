from app.routing.classifier import classify_complexity


def test_short_extraction_request_is_tier_1():
    assert classify_complexity("Extract the invoice number from this text.") == 1


def test_generic_request_is_tier_2():
    assert classify_complexity("Summarize this customer's recent activity.") == 2


def test_long_reasoning_request_is_tier_3():
    assert classify_complexity("Please analyze the root cause of this outage.") == 3


def test_very_long_request_is_tier_3_regardless_of_verbs():
    assert classify_complexity("format this data. " * 200) == 3


def test_high_risk_tag_forces_tier_3():
    assert classify_complexity("List the fields.", risk_tags=["medical"]) == 3


def test_low_risk_tag_does_not_force_tier_3():
    assert classify_complexity("Summarize this note.", risk_tags=["general"]) == 2
