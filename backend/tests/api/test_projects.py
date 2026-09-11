from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_project_crud_does_not_delete_source_directory(tmp_path: Path) -> None:
    project_root = tmp_path / "sample"
    project_root.mkdir()

    with TestClient(app) as client:
        create_response = client.post(
            "/api/v1/projects",
            json={"name": "示例项目", "rootPath": str(project_root)},
        )
        assert create_response.status_code == 201
        project = create_response.json()["data"]
        assert project["name"] == "示例项目"
        assert project["rootPath"] == str(project_root.resolve())
        assert project["scanStatus"] == "NOT_SCANNED"

        list_response = client.get("/api/v1/projects")
        assert list_response.status_code == 200
        assert list_response.json()["data"]["pagination"]["total"] == 1

        detail_response = client.get(f"/api/v1/projects/{project['id']}")
        assert detail_response.status_code == 200

        delete_response = client.delete(f"/api/v1/projects/{project['id']}")
        assert delete_response.status_code == 204

        missing_response = client.get(f"/api/v1/projects/{project['id']}")
        assert missing_response.status_code == 404
        assert missing_response.json()["error"]["code"] == "PROJECT_NOT_FOUND"

    assert project_root.exists()


def test_project_requires_absolute_directory(tmp_path: Path) -> None:
    source_file = tmp_path / "main.py"
    source_file.write_text("print('not executed')", encoding="utf-8")

    with TestClient(app) as client:
        relative_response = client.post(
            "/api/v1/projects",
            json={"name": "相对路径", "rootPath": "relative/project"},
        )
        assert relative_response.status_code == 400
        assert relative_response.json()["error"]["code"] == "INVALID_PROJECT_PATH"

        file_response = client.post(
            "/api/v1/projects",
            json={"name": "文件路径", "rootPath": str(source_file)},
        )
        assert file_response.status_code == 400
        assert file_response.json()["error"]["code"] == "INVALID_PROJECT_PATH"


def test_duplicate_project_path_is_rejected(tmp_path: Path) -> None:
    with TestClient(app) as client:
        first = client.post(
            "/api/v1/projects",
            json={"name": "项目一", "rootPath": str(tmp_path)},
        )
        second = client.post(
            "/api/v1/projects",
            json={"name": "项目二", "rootPath": str(tmp_path)},
        )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "PROJECT_PATH_EXISTS"
