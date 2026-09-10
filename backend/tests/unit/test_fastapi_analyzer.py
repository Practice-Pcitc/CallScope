from pathlib import Path

from app.analyzers.fastapi_analyzer import FastAPIProjectAnalyzer


def test_analyzer_resolves_nested_router_prefixes_and_parameters() -> None:
    root = Path(__file__).parents[1] / "fixtures" / "fastapi_sample"
    files = [
        "app/__init__.py",
        "app/main.py",
        "app/api/__init__.py",
        "app/api/users.py",
    ]

    result = FastAPIProjectAnalyzer().analyze(root=root, files=files)

    assert result.issues == []
    assert len(result.endpoints) == 2
    get_endpoint = next(
        endpoint for endpoint in result.endpoints if endpoint["http_method"] == "GET"
    )
    assert get_endpoint["path"] == "/api/v1/accounts/users/{user_id}"
    assert get_endpoint["qualified_name"] == "app.api.users.get_user"
    assert get_endpoint["summary"] == "获取用户详情"
    assert get_endpoint["tags"] == ["root", "mounted", "users"]
    assert get_endpoint["response_type"] == "UserResponse"

    parameters = {parameter["name"]: parameter for parameter in get_endpoint["parameters"]}
    assert parameters["user_id"]["location"] == "PATH"
    assert parameters["service"]["location"] == "DEPENDENCY"
    assert parameters["keyword"]["location"] == "QUERY"
    assert get_endpoint["dependencies"] == [
        {
            "parameterName": "service",
            "providerExpression": "get_user_service",
            "resolvedQualifiedName": "app.api.users.get_user_service",
            "confidence": "CONFIRMED",
        }
    ]

    post_endpoint = next(
        endpoint for endpoint in result.endpoints if endpoint["http_method"] == "POST"
    )
    assert post_endpoint["path"] == "/api/v1/accounts/users/"
    post_parameters = {parameter["name"]: parameter for parameter in post_endpoint["parameters"]}
    assert post_parameters["payload"]["location"] == "BODY"
    assert post_parameters["verbose"]["location"] == "QUERY"
    assert post_endpoint["tags"] == ["root", "mounted", "users", "write"]
    assert post_endpoint["dependencies"][0]["providerExpression"] == "audit_request"


def test_analyzer_resolves_package_modules_below_repository_root(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "backend" / "app"
    api_root = source_root / "api" / "v1"
    core_root = source_root / "core"
    api_root.mkdir(parents=True)
    core_root.mkdir()
    for package in [
        source_root / "__init__.py",
        source_root / "api" / "__init__.py",
        api_root / "__init__.py",
        core_root / "__init__.py",
    ]:
        package.write_text("", encoding="utf-8")
    (core_root / "config.py").write_text(
        "\n".join(
            [
                "class Settings:",
                '    api_prefix: str = "/api/v1"',
                "settings = Settings()",
            ]
        ),
        encoding="utf-8",
    )
    (source_root / "main.py").write_text(
        "\n".join(
            [
                "from fastapi import FastAPI",
                "from app.api.v1.router import api_router",
                "from app.core.config import settings",
                "app = FastAPI()",
                "app.include_router(api_router, prefix=settings.api_prefix)",
            ]
        ),
        encoding="utf-8",
    )
    (api_root / "router.py").write_text(
        "\n".join(
            [
                "from fastapi import APIRouter",
                "from app.api.v1 import users",
                "api_router = APIRouter()",
                "api_router.include_router(users.router)",
            ]
        ),
        encoding="utf-8",
    )
    (api_root / "users.py").write_text(
        "\n".join(
            [
                "from fastapi import APIRouter",
                'router = APIRouter(prefix="/users")',
                '@router.get("/{user_id}")',
                "def get_user(user_id: int):",
                "    return {'id': user_id}",
            ]
        ),
        encoding="utf-8",
    )
    files = [path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*.py")]

    result = FastAPIProjectAnalyzer().analyze(root=tmp_path, files=files)

    assert result.issues == []
    assert len(result.endpoints) == 1
    assert result.endpoints[0]["path"] == "/api/v1/users/{user_id}"
    assert result.endpoints[0]["qualified_name"] == "backend.app.api.v1.users.get_user"


def test_application_factories_preserve_local_scopes(tmp_path):
    (tmp_path / "main.py").write_text(
        """
from fastapi import FastAPI, APIRouter
router = APIRouter()
@router.get("/items")
def items():
    return []
def create_app():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    @app.get("/health")
    def health():
        return {}
    return app
def other_app():
    app = FastAPI()
    app.include_router(router, prefix="/other")
    return app
def unrelated():
    app = FastAPI()
    app.include_router(router, prefix="/not-mounted")
app = create_app()
""",
        encoding="utf-8",
    )
    result = FastAPIProjectAnalyzer().analyze(root=tmp_path, files=["main.py"])
    assert not result.issues
    assert {item["path"] for item in result.endpoints} == {
        "/api/v1/items",
        "/other/items",
        "/health",
    }


def test_callscope_factory_registers_its_actual_api():
    root = Path(__file__).parents[2]
    files = [p.relative_to(root).as_posix() for p in (root / "app").rglob("*.py")]
    result = FastAPIProjectAnalyzer().analyze(root=root, files=files)
    paths = {item["path"] for item in result.endpoints}
    assert "/api/v1/health" in paths
    assert "/api/v1/projects" in paths
    assert "/api/v1/projects/{project_id}/scans" in paths
    assert len(result.endpoints) >= 20
