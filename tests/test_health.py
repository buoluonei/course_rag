from fastapi.testclient import TestClient

from app.main import app


def test_liveness_returns_service_status() -> None:
    response = TestClient(app).get("/livez")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
