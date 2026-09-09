from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """通过环境变量管理运行配置。"""

    model_config = SettingsConfigDict(
        env_file=(
            Path(__file__).resolve().parents[3] / ".env",
            Path(__file__).resolve().parents[2] / ".env",
        ),
        env_prefix="CALLSCOPE_",
        extra="ignore",
    )

    app_name: str = "CallScope"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_prefix: Literal["/api/v1"] = "/api/v1"
    database_url: str = "sqlite:///./callscope.db"
    cors_origins: list[str] = ["http://localhost:5173"]
    max_scan_files: int = 10_000
    max_file_size_bytes: int = 2 * 1024 * 1024
    max_directory_entries: int = 50_000
    scan_error_limit: int = 100
    ai_provider: Literal["local", "grounded-local", "evidence", "openai-compatible"] = "local"
    ai_model: str = "grounded-local-v1"
    ai_api_key: str | None = Field(default=None, repr=False)
    ai_base_url: str = "https://api.openai.com/v1"
    ai_timeout_seconds: int = Field(default=60, gt=0, le=300)
    ai_max_retries: int = Field(default=2, ge=0, le=5)
    ai_retention_days: int = Field(default=30, ge=1)
    ai_max_context_chars: int = 80_000
    ai_max_source_chars: int = 48_000
    ai_max_source_per_node: int = 6_000
    ai_max_nodes: int = 150
    ai_max_edges: int = 250
    ai_prompt_version: str = "business-analysis-v2.2"
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

    @model_validator(mode="after")
    def validate_runtime(self) -> "Settings":
        if self.ai_provider == "openai-compatible":
            if not self.ai_api_key or not self.ai_api_key.strip():
                raise ValueError("CALLSCOPE_AI_API_KEY is required for openai-compatible")
            if not self.ai_model.strip() or self.ai_model == "grounded-local-v1":
                raise ValueError("Configure CALLSCOPE_AI_MODEL for the external provider")
        url = urlsplit(self.ai_base_url)
        if (
            not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or not (
                url.scheme == "https"
                or (url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"})
            )
        ):
            raise ValueError(
                "AI base URL requires HTTPS or a loopback HTTP host without credentials"
            )
        if "*" in self.cors_origins:
            raise ValueError("CORS requires explicit origins")
        for name in (
            "max_scan_files",
            "max_file_size_bytes",
            "max_directory_entries",
            "scan_error_limit",
            "ai_max_context_chars",
            "ai_max_source_chars",
            "ai_max_source_per_node",
            "ai_max_nodes",
            "ai_max_edges",
        ):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
