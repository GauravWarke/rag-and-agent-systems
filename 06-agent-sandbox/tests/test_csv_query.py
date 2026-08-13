import pytest

from app.tools.csv_query import CsvQueryArgs, handle


def test_filters_by_column_value():
    result = handle(CsvQueryArgs(column="plan", value="pro"))
    assert result["total_matches"] == 3
    assert all(row["plan"] == "pro" for row in result["matches"])


def test_value_match_is_case_insensitive():
    result = handle(CsvQueryArgs(column="status", value="ACTIVE"))
    assert result["total_matches"] == 4


def test_unknown_column_raises():
    with pytest.raises(ValueError):
        handle(CsvQueryArgs(column="ssn", value="123"))


def test_no_matches_returns_zero():
    result = handle(CsvQueryArgs(column="plan", value="nonexistent"))
    assert result["total_matches"] == 0
    assert result["matches"] == []
