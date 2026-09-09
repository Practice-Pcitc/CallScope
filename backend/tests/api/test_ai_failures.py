from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings
from app.llm.exceptions import AIAnalysisError
from app.llm.local_provider import GroundedLocalProvider
from app.main import create_app
from app.services.ai_analysis_service import AIAnalysisService


def test_external_background_failure_retry_and_recovery(monkeypatch):
    app = create_app()
    calls = []

    class FailingProvider:
        provider_name = "fake"
        model_name = "fake"

        def generate(self, *_):
            calls.append(1)
            raise AIAnalysisError("secret-marker")

    with TestClient(app) as client:
        project = client.post(
            "/api/v1/projects",
            json={
                "name": "AI failure",
                "rootPath": str(Path(__file__).parents[1] / "fixtures/fastapi_sample"),
            },
        ).json()["data"]
        client.post(f"/api/v1/projects/{project['id']}/scans")
        endpoint = client.get(f"/api/v1/projects/{project['id']}/endpoints").json()["data"][
            "items"
        ][0]
        url = f"/api/v1/projects/{project['id']}/endpoints/{endpoint['id']}/ai-analyses"
        monkeypatch.setattr(settings, "ai_provider", "openai-compatible")
        monkeypatch.setattr(settings, "ai_max_retries", 1)
        monkeypatch.setattr(AIAnalysisService, "_provider", staticmethod(lambda: FailingProvider()))
        response = client.post(url, json={})
        assert response.json()["data"]["status"] == "ANALYZING"
        result = client.get("/api/v1/ai-analyses/" + response.json()["data"]["analysisId"])
        assert result.json()["data"]["status"] == "FAILED"
        assert "secret-marker" not in result.text
        assert len(calls) == 2
        retry = client.post(url, json={})
        assert retry.status_code == 200
        assert retry.json()["data"]["analysisId"] != response.json()["data"]["analysisId"]
        monkeypatch.setattr(AIAnalysisService, "_provider", staticmethod(GroundedLocalProvider))
        recovered = client.post(url, json={}).json()["data"]
        result = client.get("/api/v1/ai-analyses/" + recovered["analysisId"])
        assert result.json()["data"]["status"] == "COMPLETED"
