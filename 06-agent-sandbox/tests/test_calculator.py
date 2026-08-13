import pytest

from app.tools.calculator import CalculatorArgs, handle


def test_basic_arithmetic():
    result = handle(CalculatorArgs(expression="2 + 3 * 4"))
    assert result["result"] == 14


def test_parentheses_and_power():
    result = handle(CalculatorArgs(expression="(2 + 3) ** 2"))
    assert result["result"] == 25


def test_division_by_zero_raises():
    with pytest.raises(ValueError):
        handle(CalculatorArgs(expression="1 / 0"))


def test_disallowed_syntax_raises():
    with pytest.raises(ValueError):
        handle(CalculatorArgs(expression="__import__('os').system('echo hi')"))


def test_name_reference_raises():
    with pytest.raises(ValueError):
        handle(CalculatorArgs(expression="x + 1"))
