from fastapi.testclient import TestClient

from app.main import app


def test_health_check() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["data"] == {
        "status": "ok",
        "service": "CallScope",
        "version": "0.1.0",
        "database": "ok",
    }
    assert response.headers["X-Request-ID"].startswith("req_")


def test_unknown_route_uses_error_envelope() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/not-found")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "HTTP_ERROR"
    assert response.json()["error"]["requestId"].startswith("req_")
