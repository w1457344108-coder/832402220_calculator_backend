"""Safe, bounded scientific expression parser for the calculator API."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import (
    Decimal,
    DecimalException,
    DivisionByZero,
    Inexact,
    InvalidOperation,
    Overflow,
    Rounded,
    Subnormal,
    Underflow,
    getcontext,
    localcontext,
)
import math
import re
import sys
from typing import Callable


class CalculationError(ValueError):
    """Raised when an expression is invalid."""


class DivisionByZeroError(CalculationError):
    """Raised when an expression divides by zero."""


class DomainError(CalculationError):
    """Raised when an operation is outside its mathematical domain."""


class ResultOutOfRangeError(CalculationError):
    """Raised when a literal, argument, or intermediate value exceeds a limit."""


_NUMBER = re.compile(r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
_NAME = re.compile(r"[a-zA-Z][a-zA-Z0-9]*")
_FUNCTIONS = frozenset({"sin", "cos", "tan", "sqrt", "ln", "log10", "exp"})
_PI = Decimal("3.141592653589793238462643383279502884197169399375105820974944592307816406286")
_MAX_MAGNITUDE = 10000
_MAX_DEPTH = 32
_MAX_EXPRESSION_LENGTH = 500


def _bounded(value: Decimal) -> Decimal:
    if not value.is_finite() or (value != 0 and not -_MAX_MAGNITUDE <= value.adjusted() <= _MAX_MAGNITUDE):
        raise ResultOutOfRangeError("Result out of range")
    return value


@dataclass(frozen=True)
class Token:
    kind: str
    value: str


def _tokenize(expression: str) -> list[Token]:
    if not isinstance(expression, str) or not expression.strip():
        raise CalculationError("Expression is required")
    if len(expression) > _MAX_EXPRESSION_LENGTH:
        raise CalculationError("Expression must be at most 500 characters")
    tokens: list[Token] = []
    index = 0
    while index < len(expression):
        char = expression[index]
        if char.isspace():
            index += 1
            continue
        if char in "0123456789.":
            match = _NUMBER.match(expression, index)
            if match is None:
                raise CalculationError("Invalid number")
            number = match.group()
            exponent = re.split("[eE]", number)
            if len(exponent) == 2 and abs(int(exponent[1])) > _MAX_MAGNITUDE:
                raise ResultOutOfRangeError("Scientific exponent out of range")
            tokens.append(Token("NUMBER", number))
            index = match.end()
            continue
        if char == "π":
            tokens.append(Token("CONSTANT", char))
            index += 1
            continue
        if char.isalpha():
            match = _NAME.match(expression, index)
            name = match.group() if match is not None else ""
            if name in ("pi", "e"):
                tokens.append(Token("CONSTANT", name))
            elif name in _FUNCTIONS:
                tokens.append(Token("FUNCTION", name))
            else:
                raise CalculationError("Unknown name")
            index = match.end()
            continue
        if char in "+-*/()^":
            tokens.append(Token(char, char))
            index += 1
            continue
        raise CalculationError("Unsupported character")
    tokens.append(Token("EOF", ""))
    return tokens


class _Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.position = 0
        self.depth = 0

    def nested(self, parse: Callable[[], Decimal]) -> Decimal:
        """Charge every recursive grammar edge against one shared budget."""
        if self.depth >= _MAX_DEPTH:
            raise CalculationError("Expression exceeds maximum depth of 32")
        self.depth += 1
        try:
            return parse()
        finally:
            self.depth -= 1

    def current(self) -> Token:
        return self.tokens[self.position]

    def consume(self, kind: str) -> Token:
        if self.current().kind != kind:
            raise CalculationError("Invalid expression")
        token = self.current()
        self.position += 1
        return token

    def parse(self) -> Decimal:
        value = self.parse_expression()
        if self.current().kind != "EOF":
            raise CalculationError("Invalid expression")
        return value

    def parse_expression(self) -> Decimal:
        value = self.parse_term()
        while self.current().kind in ("+", "-"):
            operator = self.current().kind
            self.position += 1
            right = self.parse_term()
            value = _bounded(value + right if operator == "+" else value - right)
        return value

    def parse_term(self) -> Decimal:
        value = self.parse_unary()
        while self.current().kind in ("*", "/"):
            operator = self.current().kind
            self.position += 1
            right = self.parse_unary()
            if operator == "*":
                value = _bounded(value * right)
            else:
                if right == 0:
                    raise DivisionByZeroError("Division by zero")
                value = _bounded(value / right)
        return value

    def parse_unary(self) -> Decimal:
        if self.current().kind in ("+", "-"):
            operator = self.current().kind
            self.position += 1
            value = self.nested(self.parse_unary)
            # A sign must not round a literal before a surrounding operation.
            return _bounded(value.copy_negate() if operator == "-" else value)
        return self.parse_power()

    def parse_power(self) -> Decimal:
        value = self.parse_primary()
        if self.current().kind == "^":
            self.position += 1
            exponent = self.nested(self.parse_unary)
            if exponent.copy_abs() > _MAX_MAGNITUDE:
                raise ResultOutOfRangeError("Power exponent out of range")
            if value == 0:
                if exponent == 0:
                    raise DomainError("Zero to the power of zero is undefined")
                if exponent < 0:
                    raise DivisionByZeroError("Division by zero")
                return Decimal(0)
            if value < 0 and exponent != exponent.to_integral_value():
                raise DomainError("A negative base requires an integer exponent")
            value = _bounded(getcontext().power(value, exponent))
        return value

    def parse_primary(self) -> Decimal:
        token = self.current()
        if token.kind == "NUMBER":
            self.position += 1
            try:
                return _bounded(Decimal(token.value))
            except InvalidOperation as exc:
                raise CalculationError("Invalid number") from exc
        if token.kind == "(":
            self.position += 1
            value = self.nested(self.parse_expression)
            self.consume(")")
            return value
        if token.kind == "CONSTANT":
            self.position += 1
            return _bounded(Decimal(1).exp() if token.value == "e" else +_PI)
        if token.kind == "FUNCTION":
            self.position += 1
            self.consume("(")
            argument = self.nested(self.parse_expression)
            self.consume(")")
            return _apply_function(token.value, argument)
        raise CalculationError("Invalid expression")


def _apply_function(name: str, argument: Decimal) -> Decimal:
    _bounded(argument)
    if name == "sqrt":
        if argument < 0:
            raise DomainError("Square root requires a nonnegative argument")
        return _bounded(argument.sqrt())
    if name in ("ln", "log10"):
        if argument <= 0:
            raise DomainError("Logarithm requires a positive argument")
        return _bounded(argument.ln() if name == "ln" else argument.log10())
    if name == "exp":
        if argument.copy_abs() > 23025:
            raise ResultOutOfRangeError("Exponential argument out of range")
        return _bounded(argument.exp())

    if argument.copy_abs() > Decimal("1e6"):
        raise ResultOutOfRangeError("Trigonometric argument out of range")
    angle = float(argument)
    if not math.isfinite(angle) or (argument != 0 and (angle == 0 or abs(angle) < sys.float_info.min)):
        raise ResultOutOfRangeError("Trigonometric argument cannot be represented safely")
    if name == "sin":
        result = math.sin(angle)
    elif name == "cos":
        result = math.cos(angle)
    else:
        if abs(math.cos(angle)) <= 1e-9:
            raise DomainError("Tangent is undefined near this angle")
        result = math.tan(angle)
    if not math.isfinite(result) or (result != 0 and abs(result) < sys.float_info.min):
        raise ResultOutOfRangeError("Trigonometric result out of range")
    formatted = format(result, ".15g")
    converted = Decimal(formatted)
    if converted != 0 and abs(float(converted)) < sys.float_info.min:
        converted = Decimal(repr(result))
    return _bounded(converted)


def _normalize(value: Decimal) -> str:
    _bounded(value)
    if value == 0:
        return "0"
    normalized = _bounded(value.normalize())
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if len(text) <= 200:
        return text
    coefficient, exponent = format(normalized, "e").split("e")
    return coefficient + "e" + str(int(exponent))


def evaluate_expression(expression: str) -> str:
    """Evaluate the fixed grammar and return a bounded decimal string."""
    try:
        with localcontext() as context:
            context.prec = 50
            context.Emax = _MAX_MAGNITUDE
            context.Emin = -_MAX_MAGNITUDE
            context.clamp = 0
            for signal in (Overflow, Underflow, Subnormal, InvalidOperation, DivisionByZero):
                context.traps[signal] = True
            for signal in (Inexact, Rounded):
                context.traps[signal] = False
            return _normalize(_Parser(_tokenize(expression)).parse())
    except (Overflow, Underflow, Subnormal, OverflowError) as exc:
        raise ResultOutOfRangeError("Result out of range") from exc
    except DivisionByZero as exc:
        raise DivisionByZeroError("Division by zero") from exc
    except DecimalException as exc:
        raise DomainError("Operation is outside its mathematical domain") from exc
    except RecursionError as exc:
        raise CalculationError("Expression exceeds maximum depth of 32") from exc
