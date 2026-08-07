from pathlib import Path

from app.analyzers.call_graph_analyzer import CallGraphAnalyzer
from app.analyzers.fastapi_analyzer import FastAPIProjectAnalyzer


def test_call_graph_resolves_service_repository_and_resources() -> None:
    root = Path(__file__).parent / "fixtures" / "fastapi_sample"
    files = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*.py")
    ]
    endpoints = FastAPIProjectAnalyzer().analyze(
        root=root,
        files=files,
    ).endpoints

    result = CallGraphAnalyzer().analyze(
        root=root,
        files=files,
        endpoints=endpoints,
    )
    nodes_by_qn = {
        node["qualified_name"]: node for node in result.nodes.values()
    }
    assert "app.services.user_service.UserService.get_user" in nodes_by_qn
    assert "app.repositories.user_repository.UserRepository.find_by_id" in nodes_by_qn
    assert any(
        relation["relation_type"] == "CALLS"
        and relation["confidence"] in {"CONFIRMED", "HIGH"}
        for relation in result.relations.values()
    )
    assert any(
        relation["relation_type"] == "USES_REDIS"
        for relation in result.relations.values()
    )
    assert any(
        relation["relation_type"] == "REQUESTS_EXTERNAL_API"
        for relation in result.relations.values()
    )
    assert any(
        node["node_type"] == "DATABASE_TABLE" and node["name"] == "users"
        for node in result.nodes.values()
    )


def test_call_graph_normalizes_imports_below_repository_root(
    tmp_path: Path,
) -> None:
    app_root = tmp_path / "backend" / "app"
    (app_root / "api").mkdir(parents=True)
    (app_root / "services").mkdir()
    (app_root / "__init__.py").write_text("", encoding="utf-8")
    (app_root / "api" / "__init__.py").write_text("", encoding="utf-8")
    (app_root / "services" / "__init__.py").write_text("", encoding="utf-8")
    (app_root / "api" / "users.py").write_text(
        "\n".join(
            [
                "from app.services.user_service import UserService",
                "service = UserService()",
                "def get_user():",
                "    return service.get_user()",
            ]
        ),
        encoding="utf-8",
    )
    (app_root / "services" / "user_service.py").write_text(
        "\n".join(
            [
                "class UserService:",
                "    def get_user(self):",
                "        return 1",
            ]
        ),
        encoding="utf-8",
    )
    files = [
        path.relative_to(tmp_path).as_posix()
        for path in tmp_path.rglob("*.py")
    ]

    result = CallGraphAnalyzer().analyze(
        root=tmp_path,
        files=files,
        endpoints=[],
    )

    target_key = (
        "method:backend.app.services.user_service.UserService.get_user"
    )
    assert any(
        relation["target_key"] == target_key
        and relation["confidence"] == "HIGH"
        for relation in result.relations.values()
    )
