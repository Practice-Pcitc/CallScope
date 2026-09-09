from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_nodes_and_endpoints_cannot_cross_projects():
    root = Path(__file__).parents[1] / "fixtures"
    with TestClient(create_app()) as client:
        ids = []
        for name in ("fastapi_sample", "spring_sample"):
            project = client.post(
                "/api/v1/projects", json={"name": name, "rootPath": str(root / name)}
            ).json()["data"]
            ids.append(project["id"])
            client.post(f"/api/v1/projects/{ids[-1]}/scans")
        endpoint = client.get(f"/api/v1/projects/{ids[0]}/endpoints").json()["data"]["items"][0]
        graph = client.get(f"/api/v1/projects/{ids[0]}/endpoints/{endpoint['id']}/graphs").json()[
            "data"
        ]
        response = client.get(f"/api/v1/projects/{ids[1]}/endpoints/{endpoint['id']}")
        assert response.status_code == 404
        response = client.get(f"/api/v1/projects/{ids[1]}/nodes/{graph['nodes'][0]['id']}/source")
        assert response.status_code == 404
