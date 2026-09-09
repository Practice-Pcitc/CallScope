"""Regenerate browser fixtures using only the bundled synthetic sample and local provider.
Run from backend: uv run python ../scripts/generate_browser_fixture.py
"""

import json
import os
from pathlib import Path

os.environ["CALLSCOPE_DATABASE_URL"] = "sqlite://"
os.environ["CALLSCOPE_AI_PROVIDER"] = "local"
os.environ["CALLSCOPE_AI_API_KEY"] = ""
from app.core.database import engine
from app.main import create_app
from app.models import Base
from fastapi.testclient import TestClient

root = Path(__file__).resolve().parents[1]
sample = root / "backend/tests/fixtures/fastapi_sample"
Base.metadata.create_all(engine)
with TestClient(create_app()) as client:
    project = client.post(
        "/api/v1/projects", json={"name": "FastAPI 示例项目", "rootPath": str(sample)}
    ).json()
    project_id = project["data"]["id"]
    prefix = f"/api/v1/projects/{project_id}"
    client.post(prefix + "/scans")
    project = client.get(prefix).json()
    endpoints = client.get(prefix + "/endpoints").json()
    endpoint = endpoints["data"]["items"][0]
    graph = client.get(prefix + f"/endpoints/{endpoint['id']}/graphs").json()
    analysis = client.post(
        prefix + f"/endpoints/{endpoint['id']}/ai-analyses", json={}
    ).json()
    fixture = {
        "project": project,
        "endpoints": endpoints,
        "graph": graph,
        "analysis": analysis,
        "scan": client.get(prefix + "/scans/latest").json(),
    }
    fixture["nodes"] = {
        node["id"]: {
            "detail": client.get(prefix + f"/nodes/{node['id']}").json(),
            "source": client.get(prefix + f"/nodes/{node['id']}/source").json(),
        }
        for node in graph["data"]["nodes"]
    }
    fixture["project"]["data"]["rootPath"] = "D:/samples/fastapi-sample"
    output = root / "frontend/tests/fixtures/workspace.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(fixture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
Base.metadata.drop_all(engine)
engine.dispose()
