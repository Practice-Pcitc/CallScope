from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """通过环境变量管理运行配置。"""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_prefix="CALLSCOPE_",
        extra="ignore",
    )

    app_name: str = "CallScope"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./callscope.db"
    cors_origins: list[str] = ["http://localhost:5173"]
    max_scan_files: int = 10_000
    max_file_size_bytes: int = 2 * 1024 * 1024
    max_directory_entries: int = 50_000
    scan_error_limit: int = 100
    ai_provider: str = "local"
    ai_model: str = "grounded-local-v1"
    ai_api_key: str | None = None
    ai_base_url: str = "https://api.openai.com/v1"
    ai_timeout_seconds: int = 60
    ai_max_retries: int = 2
    ai_max_context_chars: int = 80_000
    ai_max_source_chars: int = 48_000
    ai_max_source_per_node: int = 6_000
    ai_max_nodes: int = 150
    ai_max_edges: int = 250
    ai_prompt_version: str = "business-analysis-v2.1"
    ai_graph_version: str = "static-graph-v1"
    ignored_directories: list[str] = [
        ".git",
        ".idea",
        ".vscode",
        "node_modules",
        "venv",
        ".venv",
        "__pycache__",
        "dist",
        "build",
        "target",
        "coverage",
        ".pytest_cache",
        ".mypy_cache",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
