from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_validation_does_not_echo_input():
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/projects", json={"name": " ", "rootPath": "secret-marker"})
    assert response.status_code == 422
    assert "secret-marker" not in response.text
    assert "input" not in response.text


def test_unexpected_errors_are_safe():
    app = create_app()

    @app.get("/broken")
    def broken():
        raise RuntimeError("secret-marker")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/broken", headers={"X-Request-ID": "untrusted"})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "secret-marker" not in response.text
    assert response.headers["x-request-id"].startswith("req_")


def test_timestamps_include_timezone():
    with TestClient(create_app()) as client:
        project = client.post(
            "/api/v1/projects",
            json={
                "name": "fixture",
                "rootPath": str(Path(__file__).parents[1] / "fixtures/fastapi_sample"),
            },
        ).json()["data"]
        data = client.get(f"/api/v1/projects/{project['id']}").json()["data"]
    assert datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00")).tzinfo
