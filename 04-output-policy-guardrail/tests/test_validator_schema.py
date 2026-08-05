from app.policies.store import PolicyStore
from app.validators.schema import validate_schema

_POLICY = PolicyStore.load("data/policies.yaml").get("schema_mismatch")


def test_no_expected_schema_returns_none():
    assert validate_schema("not json at all", None, _POLICY) is None


def test_valid_json_matching_schema_returns_none():
    output = '{"answer": "yes", "confidence": 0.9}'
    finding = validate_schema(output, {"answer": "str", "confidence": "float"}, _POLICY)
    assert finding is None


def test_invalid_json_returns_finding():
    finding = validate_schema("{not valid json", {"answer": "str"}, _POLICY)
    assert finding is not None
    assert "not valid JSON" in finding.message


def test_missing_field_returns_finding():
    finding = validate_schema('{"answer": "yes"}', {"answer": "str", "confidence": "float"}, _POLICY)
    assert finding is not None
    assert "confidence" in finding.message


def test_wrong_type_returns_finding():
    finding = validate_schema('{"answer": "yes", "confidence": "high"}', {"answer": "str", "confidence": "float"}, _POLICY)
    assert finding is not None
    assert "confidence" in finding.message


def test_non_object_json_returns_finding():
    finding = validate_schema("[1, 2, 3]", {"answer": "str"}, _POLICY)
    assert finding is not None
    assert "object" in finding.message
