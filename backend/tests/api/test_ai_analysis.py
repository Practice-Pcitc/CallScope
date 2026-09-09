from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_ai_chain_analysis_is_grounded_and_cached() -> None:
    root = Path(__file__).parents[1] / "fixtures" / "spring_sample"

    with TestClient(app) as client:
        project = client.post(
            "/api/v1/projects",
            json={"name": "AI 链路测试", "rootPath": str(root)},
        ).json()["data"]
        assert client.post(f"/api/v1/projects/{project['id']}/scans").status_code == 202
        endpoints = client.get(f"/api/v1/projects/{project['id']}/endpoints").json()["data"][
            "items"
        ]
        endpoint = next(item for item in endpoints if item["httpMethod"] == "GET")
        graph = client.get(
            f"/api/v1/projects/{project['id']}/endpoints/{endpoint['id']}/graphs",
            params={"depth": 5},
        ).json()["data"]
        allowed_nodes = {item["id"] for item in graph["nodes"]}
        allowed_edges = {item["id"] for item in graph["edges"]}

        first = client.post(
            f"/api/v1/projects/{project['id']}/endpoints/{endpoint['id']}/ai-analyses",
            json={"depth": 5, "includeSource": True},
        )
        assert first.status_code == 200
        data = first.json()["data"]
        assert data["status"] == "COMPLETED"
        assert data["provider"] == "grounded-local"
        assert data["cached"] is False
        assert data["result"]["businessFlow"]
        assert data["result"]["businessSummary"]
        assert data["result"]["businessScenario"]

        bindings = [
            *data["result"]["businessFlow"],
            *data["result"]["businessRules"],
            *data["result"]["stateChanges"],
            *data["result"]["failureFlows"],
            *data["result"]["keyBusinessNodes"],
            *data["result"]["businessRisks"],
        ]
        assert all(set(item["nodeIds"]) <= allowed_nodes for item in bindings)
        assert allowed_edges

        cached = client.post(
            f"/api/v1/projects/{project['id']}/endpoints/{endpoint['id']}/ai-analyses",
            json={"depth": 5, "includeSource": True},
        ).json()["data"]
        assert cached["cached"] is True
        assert cached["analysisId"] == data["analysisId"]


def test_ai_combined_and_node_impact_analysis() -> None:
    root = Path(__file__).parents[1] / "fixtures" / "fastapi_sample"

    with TestClient(app) as client:
        project = client.post(
            "/api/v1/projects",
            json={"name": "AI 联合分析测试", "rootPath": str(root)},
        ).json()["data"]
        assert client.post(f"/api/v1/projects/{project['id']}/scans").status_code == 202
        endpoints = client.get(f"/api/v1/projects/{project['id']}/endpoints").json()["data"][
            "items"
        ]
        endpoint_ids = [item["id"] for item in endpoints]

        combined = client.post(
            f"/api/v1/projects/{project['id']}/endpoints/combined-ai-analyses",
            json={"endpointIds": endpoint_ids, "depth": 5},
        )
        assert combined.status_code == 200
        combined_data = combined.json()["data"]
        assert combined_data["scopeType"] == "COMBINED_ENDPOINTS"
        assert combined_data["result"]["businessFlow"]

        graph = client.get(
            f"/api/v1/projects/{project['id']}/endpoints/{endpoint_ids[0]}/graphs",
            params={"depth": 5},
        ).json()["data"]
        node_id = graph["nodes"][0]["id"]
        impact = client.post(
            f"/api/v1/projects/{project['id']}/nodes/{node_id}/impact-ai-analyses",
            json={"depth": 5},
        )
        assert impact.status_code == 200, impact.json()
        assert impact.json()["data"]["scopeType"] == "NODE_IMPACT"
