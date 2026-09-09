from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_graph_can_expand_and_inspect_evidence() -> None:
    root = Path(__file__).parents[1] / "fixtures" / "fastapi_sample"
    with TestClient(app) as client:
        project = client.post(
            "/api/v1/projects",
            json={"name": "拓扑测试", "rootPath": str(root)},
        ).json()["data"]
        assert client.post(f"/api/v1/projects/{project['id']}/scans").status_code == 202
        endpoints = client.get(f"/api/v1/projects/{project['id']}/endpoints").json()["data"][
            "items"
        ]
        endpoint = next(item for item in endpoints if item["httpMethod"] == "GET")

        response = client.get(f"/api/v1/projects/{project['id']}/endpoints/{endpoint['id']}/graphs")
        assert response.status_code == 200
        graph = response.json()["data"]
        assert len(graph["roots"]) == 1
        assert {edge["relationType"] for edge in graph["edges"]} == {"ROUTES_TO"}

        route_node = next(node for node in graph["nodes"] if node["type"] == "ROUTE_FUNCTION")
        children = client.get(
            f"/api/v1/projects/{project['id']}/nodes/{route_node['id']}/children"
        ).json()["data"]
        assert any(node["type"] == "SERVICE" for node in children["nodes"])
        call_edge = next(edge for edge in children["edges"] if edge["relationType"] == "CALLS")

        relation = client.get(f"/api/v1/projects/{project['id']}/relations/{call_edge['id']}")
        assert relation.status_code == 200
        assert relation.json()["data"]["evidence"]

        source = client.get(f"/api/v1/projects/{project['id']}/nodes/{route_node['id']}/source")
        assert source.status_code == 200
        assert "def get_user" in source.json()["data"]["source"]

        combined = client.post(
            f"/api/v1/projects/{project['id']}/graphs/combined",
            json={"endpointIds": [item["id"] for item in endpoints]},
        )
        assert combined.status_code == 200
        assert len(combined.json()["data"]["roots"]) == 2
