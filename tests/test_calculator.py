import pytest

from app.calculator import CalculationError, DivisionByZeroError, evaluate_expression


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("12+8", "20"),
        ("1+2*3", "7"),
        ("(1+2)*3", "9"),
        ("-5+8", "3"),
        ("3*-2", "-6"),
        ("0.1+0.2", "0.3"),
        (" 2 / 4 ", "0.5"),
    ],
)
def test_evaluate_supported_expressions(expression, expected):
    assert evaluate_expression(expression) == expected


def test_evaluate_rejects_invalid_expression():
    with pytest.raises(CalculationError):
        evaluate_expression("2+foo")


def test_evaluate_rejects_division_by_zero():
    with pytest.raises(DivisionByZeroError):
        evaluate_expression("10/(3-3)")


@pytest.mark.parametrize(
    "expression",
    [
        "",
        "1..2",
        "(1+2",
        "1+",
        "2 3",
        "__import__('os')",
        "eval(1+1)",
        "1;2",
    ],
)
def test_evaluate_rejects_malformed_expression(expression):
    with pytest.raises(CalculationError):
        evaluate_expression(expression)
