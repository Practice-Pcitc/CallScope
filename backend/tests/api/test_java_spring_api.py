from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_spring_project_scans_through_api() -> None:
    root = Path(__file__).parents[1] / "fixtures" / "spring_sample"

    with TestClient(app) as client:
        project = client.post(
            "/api/v1/projects",
            json={"name": "Spring sample", "rootPath": str(root)},
        ).json()["data"]
        assert client.post(f"/api/v1/projects/{project['id']}/scans").status_code == 202

        status = client.get(f"/api/v1/projects/{project['id']}/scans/latest").json()["data"]
        assert status["status"] == "SUCCEEDED"
        assert status["discoveredFiles"] == 3

        updated = client.get(f"/api/v1/projects/{project['id']}").json()["data"]
        assert updated["language"] == "java"
        assert updated["framework"] == "spring"
        assert updated["totalEndpoints"] == 2

        endpoints = client.get(f"/api/v1/projects/{project['id']}/endpoints").json()["data"][
            "items"
        ]
        get_endpoint = next(endpoint for endpoint in endpoints if endpoint["httpMethod"] == "GET")
        graph = client.get(
            f"/api/v1/projects/{project['id']}/endpoints/{get_endpoint['id']}/graphs",
            params={"depth": 4},
        ).json()["data"]
        assert {"API", "ROUTE_FUNCTION", "SERVICE", "REPOSITORY"} <= {
            node["type"] for node in graph["nodes"]
        }
        route = next(node for node in graph["nodes"] if node["type"] == "ROUTE_FUNCTION")
        children = client.get(
            f"/api/v1/projects/{project['id']}/nodes/{route['id']}/children"
        ).json()["data"]
        assert any(node["type"] == "SERVICE" for node in children["nodes"])
