from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_scanned_endpoints_are_available_through_api() -> None:
    root = Path(__file__).parents[1] / "fixtures" / "fastapi_sample"

    with TestClient(app) as client:
        project = client.post(
            "/api/v1/projects",
            json={"name": "FastAPI 示例", "rootPath": str(root)},
        ).json()["data"]
        scan = client.post(f"/api/v1/projects/{project['id']}/scans")
        assert scan.status_code == 202

        endpoint_response = client.get(
            f"/api/v1/projects/{project['id']}/endpoints",
            params={"httpMethod": "GET"},
        )
        assert endpoint_response.status_code == 200
        payload = endpoint_response.json()["data"]
        assert payload["pagination"]["total"] == 1
        assert payload["items"][0]["path"] == "/api/v1/accounts/users/{user_id}"
        assert payload["modules"] == ["app.api.users"]

        endpoint_id = payload["items"][0]["id"]
        detail = client.get(f"/api/v1/projects/{project['id']}/endpoints/{endpoint_id}")
        assert detail.status_code == 200
        assert detail.json()["data"]["functionName"] == "get_user"

        updated_project = client.get(f"/api/v1/projects/{project['id']}").json()["data"]
        assert updated_project["totalEndpoints"] == 2
