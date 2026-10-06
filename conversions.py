"""Fixed, bounded integer-base and physical-unit conversion tools."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, Inexact, ROUND_HALF_EVEN, Rounded, localcontext
from fractions import Fraction
import re


_ERROR_CODES = frozenset({
    "INVALID_BASE_NUMBER", "INVALID_UNIT_VALUE", "INVALID_UNIT_PAIR",
    "TEMPERATURE_BELOW_ABSOLUTE_ZERO", "RESULT_OUT_OF_RANGE",
})
_BASE_DIGITS = {2: "[01]+", 8: "[0-7]+", 10: "[0-9]+", 16: "[0-9a-fA-F]+"}
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE]([+-]?[0-9]+))?")
_MIN_MAGNITUDE = Fraction(1, 10**10000)
_MAX_EXCLUSIVE = Fraction(10**10001)


class ConversionError(ValueError):
    def __init__(self, code: str):
        if code not in _ERROR_CODES:
            raise ValueError("Unknown conversion error code")
        super().__init__(code)
        self.code = code


def convert_base(value: str, from_base: int, to_base: int) -> str:
    if (type(from_base) is not int or type(to_base) is not int
            or from_base not in _BASE_DIGITS or to_base not in _BASE_DIGITS
            or not isinstance(value, str) or len(value) > 400):
        raise ConversionError("INVALID_BASE_NUMBER")
    text = value.strip()
    digits = text[1:] if text.startswith(("+", "-")) else text
    if digits.lower().startswith(("0b", "0o", "0x")) or re.fullmatch(_BASE_DIGITS[from_base], digits) is None:
        raise ConversionError("INVALID_BASE_NUMBER")
    integer = int(text, from_base)
    magnitude = abs(integer)
    if to_base == 2:
        numeric = format(magnitude, "b")
    elif to_base == 8:
        numeric = format(magnitude, "o")
    elif to_base == 16:
        numeric = format(magnitude, "X")
    else:
        numeric = str(magnitude)
    result = ("-" if integer < 0 else "") + numeric
    if len(result) > 200:
        raise ConversionError("RESULT_OUT_OF_RANGE")
    return result


def _parse_unit_value(value: str) -> Fraction:
    if not isinstance(value, str) or len(value) > 100:
        raise ConversionError("INVALID_UNIT_VALUE")
    text = value.strip()
    match = _NUMBER.fullmatch(text)
    if match is None:
        raise ConversionError("INVALID_UNIT_VALUE")
    exponent = match.group(1)
    if exponent is not None and abs(int(exponent)) > 10000:
        raise ConversionError("RESULT_OUT_OF_RANGE")
    amount = Decimal(text)
    digits = list(amount.as_tuple().digits)
    while digits and digits[0] == 0:
        digits.pop(0)
    while digits and digits[-1] == 0:
        digits.pop()
    if len(digits) > 50:
        raise ConversionError("INVALID_UNIT_VALUE")
    if amount != 0 and not -10000 <= amount.adjusted() <= 10000:
        raise ConversionError("RESULT_OUT_OF_RANGE")
    return Fraction(amount)


def format_unit_result(exact: Fraction) -> str:
    """Round once to 50 digits, preserving loss-of-precision information."""
    if exact == 0:
        return "0"
    if not _MIN_MAGNITUDE <= abs(exact) < _MAX_EXCLUSIVE:
        raise ConversionError("RESULT_OUT_OF_RANGE")
    with localcontext() as context:
        context.prec = 50
        context.rounding = ROUND_HALF_EVEN
        context.Emax = 10050
        context.Emin = -10050
        context.traps[Inexact] = False
        context.traps[Rounded] = False
        rounded = Decimal(exact.numerator) / Decimal(exact.denominator)
    if not -10000 <= rounded.adjusted() <= 10000:
        raise ConversionError("RESULT_OUT_OF_RANGE")
    approximate = Fraction(rounded) != exact
    sign, original_digits, exponent = rounded.as_tuple()
    digits = list(original_digits)
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
        exponent += 1
    digit_text = "".join(str(digit) for digit in digits)
    point = len(digits) + exponent
    if exponent >= 0:
        fixed_length = sign + point
    elif point > 0:
        fixed_length = sign + len(digits) + 1
    else:
        fixed_length = sign + 2 - point + len(digits)
    if fixed_length <= 80:
        numeric = format(Decimal((sign, tuple(digits), exponent)), "f")
    else:
        mantissa = digit_text[0]
        if len(digit_text) > 1:
            mantissa += "." + digit_text[1:]
        adjusted = len(digits) + exponent - 1
        numeric = ("-" if sign else "") + mantissa + f"e{adjusted:+d}"
    result = ("≈" if approximate else "") + numeric
    if len(result) > 200:
        raise ConversionError("RESULT_OUT_OF_RANGE")
    return result


@dataclass(frozen=True)
class _Unit:
    id: str
    symbol: str
    zh: str
    en: str
    scale: Fraction
    shift: Fraction


@dataclass(frozen=True)
class _Category:
    id: str
    zh: str
    en: str
    reference: str
    units: tuple[_Unit, ...]


def _unit(id: str, symbol: str, zh: str, en: str, scale: str | Fraction = "1", shift: str = "0") -> _Unit:
    ratio = scale if isinstance(scale, Fraction) else Fraction(Decimal(scale))
    return _Unit(id, symbol, zh, en, ratio, Fraction(Decimal(shift)))


# The sole catalog: both arithmetic and display relationships come from it.
_CATEGORIES = (
    _Category("length", "长度", "Length", "m", (
        _unit("nm", "nm", "纳米", "Nanometre", "0.000000001"),
        _unit("um", "μm", "微米", "Micrometre", "0.000001"),
        _unit("mm", "mm", "毫米", "Millimetre", "0.001"),
        _unit("cm", "cm", "厘米", "Centimetre", "0.01"),
        _unit("m", "m", "米", "Metre"),
        _unit("km", "km", "千米", "Kilometre", "1000"),
    )),
    _Category("mass", "质量", "Mass", "kg", (
        _unit("mg", "mg", "毫克", "Milligram", "0.000001"),
        _unit("g", "g", "克", "Gram", "0.001"),
        _unit("kg", "kg", "千克", "Kilogram"),
        _unit("t", "t", "公吨", "Tonne", "1000"),
    )),
    _Category("area", "面积", "Area", "m²", (
        _unit("mm2", "mm²", "平方毫米", "Square millimetre", "0.000001"),
        _unit("cm2", "cm²", "平方厘米", "Square centimetre", "0.0001"),
        _unit("m2", "m²", "平方米", "Square metre"),
        _unit("ha", "ha", "公顷", "Hectare", "10000"),
        _unit("km2", "km²", "平方千米", "Square kilometre", "1000000"),
    )),
    _Category("volume", "体积", "Volume", "m³", (
        _unit("ml", "mL", "毫升", "Millilitre", "0.000001"),
        _unit("cm3", "cm³", "立方厘米", "Cubic centimetre", "0.000001"),
        _unit("l", "L", "升", "Litre", "0.001"),
        _unit("dm3", "dm³", "立方分米", "Cubic decimetre", "0.001"),
        _unit("m3", "m³", "立方米", "Cubic metre"),
    )),
    _Category("time", "时间", "Time", "s", (
        _unit("ms", "ms", "毫秒", "Millisecond", "0.001"),
        _unit("s", "s", "秒", "Second"),
        _unit("min", "min", "分钟", "Minute", "60"),
        _unit("h", "h", "小时", "Hour", "3600"),
        _unit("d", "d", "天", "Day", "86400"),
    )),
    _Category("temperature", "温度", "Temperature", "K", (
        _unit("c", "°C", "摄氏度", "Celsius", "1", "273.15"),
        _unit("f", "°F", "华氏度", "Fahrenheit", Fraction(5, 9), "459.67"),
        _unit("k", "K", "开尔文", "Kelvin"),
    )),
)


def _selected_units(category: str, from_unit: str, to_unit: str) -> tuple[_Category, _Unit, _Unit]:
    selected = next((item for item in _CATEGORIES if item.id == category), None)
    if selected is None:
        raise ConversionError("INVALID_UNIT_PAIR")
    source = next((unit for unit in selected.units if unit.id == from_unit), None)
    target = next((unit for unit in selected.units if unit.id == to_unit), None)
    if source is None or target is None:
        raise ConversionError("INVALID_UNIT_PAIR")
    return selected, source, target


def convert_unit(value: str, category: str, from_unit: str, to_unit: str) -> str:
    selected, source, target = _selected_units(category, from_unit, to_unit)
    amount = _parse_unit_value(value)
    reference = (amount + source.shift) * source.scale
    if selected.id == "temperature" and reference < 0:
        raise ConversionError("TEMPERATURE_BELOW_ABSOLUTE_ZERO")
    exact = reference / target.scale - target.shift
    return format_unit_result(exact)


def describe_unit_conversion(value: str, category: str, from_unit: str, to_unit: str) -> str:
    _, source, target = _selected_units(category, from_unit, to_unit)
    return f"UNIT {value.strip()} {source.symbol} → {target.symbol}"


def get_conversion_options() -> dict[str, object]:
    categories = []
    for category in _CATEGORIES:
        units = []
        for unit in category.units:
            if category.id == "temperature":
                source = unit.symbol
                if unit.shift:
                    source += " + " + format_unit_result(unit.shift)
                if unit.scale != 1:
                    source = f"({source}) × {unit.scale.numerator}/{unit.scale.denominator}"
                relation = f"{category.reference} = {source}"
                minimum = format_unit_result(-unit.shift)
            else:
                relation = f"1 {unit.symbol} = {format_unit_result(unit.scale)} {category.reference}"
                minimum = None
            units.append({
                "id": unit.id, "symbol": unit.symbol, "name": {"zh": unit.zh, "en": unit.en},
                "relation": relation, "minimum": minimum,
            })
        categories.append({
            "id": category.id, "name": {"zh": category.zh, "en": category.en},
            "reference": category.reference, "units": units,
        })
    return {
        "bases": [
            {"id": 2, "digits": "0–1", "example": "11111111"},
            {"id": 8, "digits": "0–7", "example": "377"},
            {"id": 10, "digits": "0–9", "example": "255"},
            {"id": 16, "digits": "0–9, A–F", "example": "FF"},
        ],
        "categories": categories,
    }
