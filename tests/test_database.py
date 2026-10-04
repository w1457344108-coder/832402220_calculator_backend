import os
from pathlib import Path
import subprocess
import sys
import textwrap

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

import pytest

from app.database import normalize_database_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "postgresql://user:password@example.test:5432/calculator",
            "postgresql+psycopg://user:password@example.test:5432/calculator",
        ),
        (
            "postgresql+psycopg://user:password@example.test:5432/calculator",
            "postgresql+psycopg://user:password@example.test:5432/calculator",
        ),
        ("sqlite+pysqlite:///./calculator.db", "sqlite+pysqlite:///./calculator.db"),
    ],
)
def test_normalize_database_url(url, expected):
    assert normalize_database_url(url) == expected


def test_engine_reconnects_after_pooled_connection_is_closed(tmp_path):
    script = textwrap.dedent(
        """
        from sqlalchemy import text
        from app.database import engine

        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
            connection.commit()
            raw_connection = connection.connection.dbapi_connection

        # Simulate the server closing an idle connection already back in the pool.
        raw_connection.close()

        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1

        engine.dispose()
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env={
            **os.environ,
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'reconnect.db'}",
        },
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
