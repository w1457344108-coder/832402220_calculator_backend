import os

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
