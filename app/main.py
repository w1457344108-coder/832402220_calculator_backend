from __future__ import annotations

import os
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .calculator import (
    CalculationError,
    DivisionByZeroError,
    DomainError,
    ResultOutOfRangeError,
    evaluate_expression,
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
        "NOT_FOUND": {"zh": "记录不存在", "en": "Record not found"},
    }[code]


def _history_item(record: CalculationHistory) -> dict[str, object]:
    created_at: datetime = record.created_at
    return {"id": record.id, "expression": record.expression, "result": record.result, "created_at": created_at.isoformat()}


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
    if len(result) > 200:
        # Keep the database contract defensive if the evaluator changes later.
        raise HTTPException(status_code=400, detail={"success": False, "code": "RESULT_OUT_OF_RANGE", "message": _message("RESULT_OUT_OF_RANGE")})
    record = CalculationHistory(expression=payload.expression.strip(), result=result)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"success": True, "id": record.id, "expression": record.expression, "result": record.result, "created_at": record.created_at.isoformat()}


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
