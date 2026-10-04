"""Safe arithmetic expression parser for the calculator API."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext


class CalculationError(ValueError):
    """Raised when an expression is invalid."""


class DivisionByZeroError(CalculationError):
    """Raised when an expression divides by zero."""


@dataclass(frozen=True)
class Token:
    kind: str
    value: str


def _tokenize(expression: str) -> list[Token]:
    if not isinstance(expression, str) or not expression.strip():
        raise CalculationError("Expression is required")
    tokens: list[Token] = []
    index = 0
    while index < len(expression):
        char = expression[index]
        if char.isspace():
            index += 1
            continue
        if char.isdigit() or char == ".":
            start = index
            dots = 0
            digits = 0
            while index < len(expression) and (expression[index].isdigit() or expression[index] == "."):
                if expression[index] == ".":
                    dots += 1
                else:
                    digits += 1
                index += 1
            if dots > 1 or digits == 0:
                raise CalculationError("Invalid number")
            tokens.append(Token("NUMBER", expression[start:index]))
            continue
        if char in "+-*/()":
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
            value = value + right if operator == "+" else value - right
        return value

    def parse_term(self) -> Decimal:
        value = self.parse_unary()
        while self.current().kind in ("*", "/"):
            operator = self.current().kind
            self.position += 1
            right = self.parse_unary()
            if operator == "*":
                value *= right
            else:
                if right == 0:
                    raise DivisionByZeroError("Division by zero")
                value /= right
        return value

    def parse_unary(self) -> Decimal:
        if self.current().kind == "+":
            self.position += 1
            return self.parse_unary()
        if self.current().kind == "-":
            self.position += 1
            return -self.parse_unary()
        return self.parse_primary()

    def parse_primary(self) -> Decimal:
        token = self.current()
        if token.kind == "NUMBER":
            self.position += 1
            try:
                return Decimal(token.value)
            except InvalidOperation as exc:
                raise CalculationError("Invalid number") from exc
        if token.kind == "(":
            self.position += 1
            value = self.parse_expression()
            self.consume(")")
            return value
        raise CalculationError("Invalid expression")


def _normalize(value: Decimal) -> str:
    if value == 0:
        return "0"
    normalized = value.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def evaluate_expression(expression: str) -> str:
    """Evaluate supported arithmetic and return a normalized decimal string."""
    with localcontext() as context:
        context.prec = 50
        return _normalize(_Parser(_tokenize(expression)).parse())
