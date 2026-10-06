from __future__ import annotations

import os
from datetime import datetime
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, StrictInt, StrictStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from .calculator import (
    CalculationError,
    DivisionByZeroError,
    DomainError,
    ResultOutOfRangeError,
    evaluate_expression,
)
from .conversions import (
    ConversionError,
    convert_base,
    convert_unit,
    describe_unit_conversion,
    get_conversion_options,
)
from .database import Base, engine, get_db
from .models import CalculationHistory


app = FastAPI(title="Calculator API")
allowed_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


class CalculateRequest(BaseModel):
    expression: str = Field(min_length=1, max_length=500)


class BaseConversionRequest(BaseModel):
    value: StrictStr = Field(min_length=1, max_length=400)
    from_base: StrictInt
    to_base: StrictInt


UnitCategory = Literal["length", "mass", "area", "volume", "time", "temperature"]


class UnitConversionRequest(BaseModel):
    category: UnitCategory
    value: StrictStr = Field(min_length=1, max_length=100)
    from_unit: StrictStr = Field(min_length=1, max_length=8)
    to_unit: StrictStr = Field(min_length=1, max_length=8)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "success" in exc.detail:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return Response(status_code=exc.status_code, content=str(exc.detail))


def _message(code: str) -> dict[str, str]:
    return {
        "INVALID_EXPRESSION": {"zh": "表达式无效", "en": "Invalid expression"},
        "DIVISION_BY_ZERO": {"zh": "除数不能为零", "en": "Division by zero is not allowed"},
        "DOMAIN_ERROR": {"zh": "数值超出定义域", "en": "Operation is outside its domain"},
        "RESULT_OUT_OF_RANGE": {"zh": "结果超出范围", "en": "Result is out of range"},
        "INVALID_INPUT": {"zh": "输入格式无效，请检查输入后重试", "en": "Invalid input. Check the input and try again"},
        "INVALID_BASE_NUMBER": {"zh": "进制整数无效", "en": "Invalid integer for the selected base"},
        "INVALID_UNIT_VALUE": {"zh": "单位数值无效", "en": "Invalid unit value"},
        "INVALID_UNIT_PAIR": {"zh": "单位组合无效", "en": "Invalid unit pair"},
        "TEMPERATURE_BELOW_ABSOLUTE_ZERO": {"zh": "温度低于绝对零度", "en": "Temperature is below absolute zero"},
        "NOT_FOUND": {"zh": "记录不存在", "en": "Record not found"},
    }[code]


def _history_item(record: CalculationHistory) -> dict[str, object]:
    created_at: datetime = record.created_at
    return {"id": record.id, "expression": record.expression, "result": record.result, "created_at": created_at.isoformat()}


def _conversion_error(error: ConversionError) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={"success": False, "code": error.code, "message": _message(error.code)},
    )


def save_history(db: Session, expression: str, result: str) -> dict[str, object]:
    if len(expression) > 500 or len(result) > 200:
        raise HTTPException(status_code=400, detail={"success": False, "code": "RESULT_OUT_OF_RANGE", "message": _message("RESULT_OUT_OF_RANGE")})
    record = CalculationHistory(expression=expression, result=result)
    db.add(record)
    try:
        db.flush()
        response = {"success": True, **_history_item(record)}
        db.commit()
    except Exception:
        db.rollback()
        raise
    return response


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/calculate")
def calculate(payload: CalculateRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        result = evaluate_expression(payload.expression)
    except DivisionByZeroError:
        raise HTTPException(status_code=400, detail={"success": False, "code": "DIVISION_BY_ZERO", "message": _message("DIVISION_BY_ZERO")})
    except DomainError:
        raise HTTPException(status_code=400, detail={"success": False, "code": "DOMAIN_ERROR", "message": _message("DOMAIN_ERROR")})
    except ResultOutOfRangeError:
        raise HTTPException(status_code=400, detail={"success": False, "code": "RESULT_OUT_OF_RANGE", "message": _message("RESULT_OUT_OF_RANGE")})
    except CalculationError:
        raise HTTPException(status_code=400, detail={"success": False, "code": "INVALID_EXPRESSION", "message": _message("INVALID_EXPRESSION")})
    return save_history(db, payload.expression.strip(), result)


@app.get("/api/convert/options")
def conversion_options() -> dict[str, object]:
    return get_conversion_options()


@app.post("/api/convert/base")
def base_conversion(payload: BaseConversionRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        result = convert_base(payload.value, payload.from_base, payload.to_base)
    except ConversionError as error:
        raise _conversion_error(error)
    expression = f"BASE {payload.value.strip()} ({payload.from_base}) → ({payload.to_base})"
    return save_history(db, expression, result)


@app.post("/api/convert/unit")
def unit_conversion(payload: UnitConversionRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        result = convert_unit(payload.value, payload.category, payload.from_unit, payload.to_unit)
        expression = describe_unit_conversion(payload.value, payload.category, payload.from_unit, payload.to_unit)
    except ConversionError as error:
        raise _conversion_error(error)
    return save_history(db, expression, result)


@app.get("/api/history")
def history(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    records = db.scalars(select(CalculationHistory).order_by(CalculationHistory.created_at.desc(), CalculationHistory.id.desc())).all()
    return [_history_item(record) for record in records]


@app.delete("/api/history/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history(record_id: int, db: Session = Depends(get_db)) -> Response:
    record = db.get(CalculationHistory, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"success": False, "code": "NOT_FOUND", "message": _message("NOT_FOUND")})
    db.delete(record)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
