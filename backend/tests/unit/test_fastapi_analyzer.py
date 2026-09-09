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
