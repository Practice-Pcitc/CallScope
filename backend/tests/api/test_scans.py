from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_scan_discovers_python_files_and_ignores_configured_directories(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("x = 1", encoding="utf-8")
    (tmp_path / "service.py").write_text("y = 2", encoding="utf-8")
    (tmp_path / "README.md").write_text("docs", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "ignored.py").write_text("ignored = True", encoding="utf-8")
    (tmp_path / "target").mkdir()
    (tmp_path / "target" / "copied.py").write_text(
        "copied = True",
        encoding="utf-8",
    )
    (tmp_path / "large.py").write_text("z = 'too large'", encoding="utf-8")
    monkeypatch.setattr(settings, "max_file_size_bytes", 12)

    with TestClient(app) as client:
        project_response = client.post(
            "/api/v1/projects",
            json={"name": "扫描示例", "rootPath": str(tmp_path)},
        )
        project_id = project_response.json()["data"]["id"]

        start_response = client.post(f"/api/v1/projects/{project_id}/scans")
        assert start_response.status_code == 202

        status_response = client.get(f"/api/v1/projects/{project_id}/scans/latest")
        assert status_response.status_code == 200
        scan = status_response.json()["data"]
        assert scan["status"] == "SUCCEEDED"
        assert scan["progress"] == 100
        assert scan["discoveredFiles"] == 2
        assert scan["processedFiles"] == 2
        assert scan["skippedFiles"] == 1
        assert scan["errors"][0]["code"] == "FILE_TOO_LARGE"

        project = client.get(f"/api/v1/projects/{project_id}").json()["data"]
        assert project["scanStatus"] == "READY"
        assert project["totalFiles"] == 2
        assert project["activeRevisionId"] == scan["revisionId"]


def test_scan_status_requires_existing_task(tmp_path: Path) -> None:
    with TestClient(app) as client:
        project = client.post(
            "/api/v1/projects",
            json={"name": "未扫描项目", "rootPath": str(tmp_path)},
        ).json()["data"]
        response = client.get(f"/api/v1/projects/{project['id']}/scans/latest")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SCAN_NOT_FOUND"
