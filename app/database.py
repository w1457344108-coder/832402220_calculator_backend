"""Database setup for PostgreSQL in production and SQLite in tests."""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def normalize_database_url(url: str) -> str:
    """Use the psycopg 3 SQLAlchemy dialect for Neon PostgreSQL URLs."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = normalize_database_url(
    os.getenv("DATABASE_URL", "sqlite+pysqlite:///./calculator.db")
)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine_kwargs = {"future": True, "connect_args": connect_args}
if DATABASE_URL in {"sqlite:///:memory:", "sqlite+pysqlite:///:memory:"}:
    engine_kwargs["poolclass"] = StaticPool
engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
