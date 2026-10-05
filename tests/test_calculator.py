from decimal import Decimal, localcontext

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


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("1/3", "0." + "3" * 50),
        ("2e3", "2000"),
        ("1.E+2", "100"),
        (".5e-2", "0.005"),
        ("2^3^2", "512"),
        ("-2^2", "-4"),
        ("(-2)^2", "4"),
        ("2^-3", "0.125"),
        ("2^-3^2", "0.001953125"),
        ("2^+3", "8"),
        ("(-2)^-3", "-0.125"),
        ("(-2)^2.000", "4"),
        ("sqrt(9)", "3"),
        ("ln(1)", "0"),
        ("log10(100)", "2"),
        ("exp(0)", "1"),
        ("sin(0)", "0"),
        ("cos(0)", "1"),
        ("tan(0)", "0"),
        ("sqrt(exp(ln(16)))+log10(100)*2^3", "20"),
        ("0^2", "0"),
        ("0^0.5", "0"),
        ("(-0)^3", "0"),
        ("1^10000", "1"),
        ("1^-10000", "1"),
        ("0e-10000", "0"),
        ("0e10000", "0"),
    ],
)
def test_scientific_exact_results(expression, expected):
    assert evaluate_expression(expression) == expected


def test_decimal_literals_are_not_rounded_before_arithmetic():
    expression = "1" + "0" * 50 + "1-1" + "0" * 51
    assert evaluate_expression(expression) == "1"


def test_constants_share_the_fifty_digit_decimal_context():
    assert evaluate_expression("pi") == evaluate_expression("π")
    assert evaluate_expression("pi") == "3.1415926535897932384626433832795028841971693993751"
    assert evaluate_expression("e") == evaluate_expression("exp(1)")
    assert evaluate_expression("e") == "2.7182818284590452353602874713526624977572470937"
    with localcontext() as context:
        context.prec = 50
        assert Decimal(evaluate_expression("2*e")) == Decimal(2) * Decimal(1).exp()


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("sqrt(2)", "1.4142135623730950488016887242096980785696718753769"),
        ("ln(2)", "0.69314718055994530941723212145817656807550013436026"),
        ("log10(2)", "0.30102999566398119521373889472449302676818988146211"),
        ("2^0.5", "1.4142135623730950488016887242096980785696718753769"),
    ],
)
def test_decimal_scientific_precision(expression, expected):
    assert evaluate_expression(expression) == expected


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("sin(pi/6)", 0.5),
        ("cos(pi)", -1.0),
        ("tan(pi/4)", 1.0),
        ("sin(-pi/2)", -1.0),
    ],
)
def test_trigonometry_uses_radians(expression, expected):
    assert float(evaluate_expression(expression)) == pytest.approx(expected, abs=1e-12)


def test_trigonometry_preserves_minimum_normal_results_for_nesting():
    result = evaluate_expression("sin(2.2250738585072014e-308)")
    assert result == "2.2250738585072014e-308"
    nested = evaluate_expression("sin(sin(2.2250738585072014e-308))")
    assert nested == result


def test_small_normal_trigonometric_result_is_preserved():
    assert evaluate_expression("sin(1e-307)") == "1e-307"


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("sin(1000000)", -0.3499935021712929521176524867807715),
        ("cos(1000000)", 0.9367521275331447869385325350749188),
        ("tan(1000000)", -0.373624453987599029173497088575381),
        ("sin(-1000000)", 0.3499935021712929521176524867807715),
    ],
)
def test_large_angles_match_independent_reference_values(expression, expected):
    assert float(evaluate_expression(expression)) == pytest.approx(expected, abs=1e-9)


@pytest.mark.parametrize(
    "expression",
    [
        "2e", "1e+", "1e2e3", "2 e3", "1e-", "2e+e", "2π", "2pi", "2(3)",
        "(2)(3)", "sin(0)cos(0)", "sqrt 4", "sin()", "sin(1,2)", "sin(1)(2)",
        "PI", "Sin(0)", "pi(1)", "e(1)", "foo(1)", "sin", "nan", "Infinity",
        "NaN", "1e1.5", "1.2.3", "'1'", '"1"', "pi.real", "sqrt.__class__",
        "__import__('os').system('id')", "exec(1)", "getattr(pi, 'real')", "[1]",
        "1//2", "1**2", "1%2", "1^", "^2", "1,2",
    ],
)
def test_scientific_parser_rejects_unsupported_syntax(expression):
    with pytest.raises(CalculationError):
        evaluate_expression(expression)


@pytest.mark.parametrize(
    "expression",
    [
        "sqrt(-1)", "ln(0)", "ln(-1)", "log10(0)", "log10(-1)", "0^0",
        "(-2)^0.5", "(-2)^2.000000000000000000000000000000000000000000000000001",
        "tan(pi/2)", "tan(-pi/2)", "tan(pi/2+0.0000000001)",
    ],
)
def test_domain_errors_have_a_dedicated_business_exception(expression):
    with pytest.raises(CalculationError) as error:
        evaluate_expression(expression)
    assert type(error.value).__name__ == "DomainError"


@pytest.mark.parametrize("expression", ["0^-1", "0^-0.5", "1/sin(0)"])
def test_scientific_zero_division_keeps_existing_exception(expression):
    with pytest.raises(DivisionByZeroError):
        evaluate_expression(expression)


@pytest.mark.parametrize(
    "expression",
    [
        "1e10001", "1e-10001", "0e10001", "0e-10001", "10e10000", ".1e-10000",
        "1e10000*10", "1e-10000/10", "1e-10000*0.1", "1e10000+1e10000*9",
        "10^10000*10", "10^-10000/10", "1^10001", "1^-10001", "0^10001",
        "exp(23025.0001)", "exp(-23025.0001)", "exp(1e10000)",
        "sin(1000000.0001)", "cos(-1000000.0001)", "tan(1000001)",
        "sin(1e-10000)", "cos(1e-10000)", "tan(1e-10000)", "sin(1e-308)",
        "sin(1e-324)", "sin(-1e-324)", "sin(2.225073858507201e-308)",
    ],
)
def test_numeric_range_errors_have_a_dedicated_business_exception(expression):
    with pytest.raises(CalculationError) as error:
        evaluate_expression(expression)
    assert type(error.value).__name__ == "ResultOutOfRangeError"


@pytest.mark.parametrize(
    ("expression", "adjusted"),
    [
        ("1e10000", 10000), ("1e-10000", -10000), ("10^10000", 10000),
        ("10^-10000", -10000), ("exp(23025)", 9999), ("exp(-23025)", -10000),
    ],
)
def test_numeric_range_boundaries_are_supported(expression, adjusted):
    result = Decimal(evaluate_expression(expression))
    assert result.is_finite()
    assert result.adjusted() == adjusted


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("10^199", "1" + "0" * 199),
        ("10^200", "1e200"),
        ("-10^198", "-1" + "0" * 198),
        ("-10^199", "-1e199"),
        ("10^-198", "0." + "0" * 197 + "1"),
        ("10^-199", "1e-199"),
        ("9" * 201, "1e201"),
        ("-" + "9" * 201, "-1e201"),
    ],
)
def test_output_uses_fixed_form_until_two_hundred_characters(expression, expected):
    assert evaluate_expression(expression) == expected


@pytest.mark.parametrize(
    "expression",
    ["1e10000", "1e-10000", "-10^199", "10^-199", "exp(23025)", "exp(-23025)", "9" * 201],
)
def test_scientific_output_is_bounded_and_reparseable(expression):
    result = evaluate_expression(expression)
    assert len(result) <= 200
    assert "E" not in result
    assert evaluate_expression(result) == result


def test_small_trigonometric_residual_is_not_rounded_to_zero():
    result = Decimal(evaluate_expression("sin(pi)"))
    assert 0 < abs(result) < Decimal("1e-12")


@pytest.mark.parametrize("depth", [32, 33])
@pytest.mark.parametrize("structure", ["parentheses", "function", "unary", "power", "mixed"])
def test_semantic_depth_is_shared_by_all_recursive_structures(structure, depth):
    if structure == "parentheses":
        expression = "(" * depth + "1" + ")" * depth
    elif structure == "function":
        expression = "sqrt(" * depth + "1" + ")" * depth
    elif structure == "unary":
        expression = "+" * depth + "1"
    elif structure == "power":
        expression = "1^" * depth + "1"
    else:
        expression = "sqrt((+1^" * 8 + ("+1" if depth == 33 else "1") + "))" * 8
    if depth == 32:
        assert evaluate_expression(expression) == "1"
    else:
        with pytest.raises(CalculationError, match="depth"):
            evaluate_expression(expression)


@pytest.mark.parametrize("operator", ["+", "*"])
def test_long_flat_expressions_do_not_accumulate_semantic_depth(operator):
    expression = operator.join(["1"] * 250)
    assert evaluate_expression(expression) == ("250" if operator == "+" else "1")


@pytest.mark.parametrize("length", [500, 501])
def test_parser_checks_the_original_expression_length(length):
    expression = "1" + " " * (length - 1)
    if length == 500:
        assert evaluate_expression(expression) == "1"
    else:
        with pytest.raises(CalculationError, match="500"):
            evaluate_expression(expression)


def test_scientific_exponent_sign_does_not_consume_semantic_depth():
    assert evaluate_expression("+" * 32 + "1e-3") == "0.001"
