import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


def setup_module():
    Base.metadata.create_all(bind=engine)


def teardown_module():
    Base.metadata.drop_all(bind=engine)


def test_health_endpoint():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_calculate_history_and_delete():
    client = TestClient(app)
    calculated = client.post("/api/calculate", json={"expression": "(1+2)*3"})
    assert calculated.status_code == 200
    body = calculated.json()
    assert body["success"] is True
    assert body["result"] == "9"
    assert body["expression"] == "(1+2)*3"
    record_id = body["id"]

    history = client.get("/api/history")
    assert history.status_code == 200
    assert history.json()[0]["id"] == record_id

    deleted = client.delete(f"/api/history/{record_id}")
    assert deleted.status_code == 204
    assert client.get("/api/history").json() == []


def test_calculate_returns_bilingual_error():
    response = TestClient(app).post("/api/calculate", json={"expression": "1/0"})
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "DIVISION_BY_ZERO"
    assert "zh" in body["message"] and "en" in body["message"]
