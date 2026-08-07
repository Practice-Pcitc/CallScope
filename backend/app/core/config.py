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
