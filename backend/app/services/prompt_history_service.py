from __future__ import annotations

import sqlite3
from typing import Any

from app.core.exceptions import AppException
from app.repositories.prompt_history_repository import PromptHistoryRepository


class PromptHistoryService:
    def __init__(self) -> None:
        self.repository = PromptHistoryRepository()

    def list(self, **filters: Any) -> tuple[list[dict[str, Any]], int]:
        try:
            return self.repository.list(**filters)
        except (OSError, sqlite3.Error) as exc:
            raise self._unavailable(exc) from exc

    def get(self, record_id: str) -> dict[str, Any]:
        try:
            record = self.repository.get(record_id)
        except (OSError, sqlite3.Error) as exc:
            raise self._unavailable(exc) from exc
        if not record:
            raise AppException(
                code="PROMPT_RECORD_NOT_FOUND",
                message="Prompt 记录不存在",
                status_code=404,
            )
        return record

    def list_sessions(self, **filters: Any) -> tuple[list[dict[str, Any]], int]:
        try:
            return self.repository.list_sessions(**filters)
        except (OSError, sqlite3.Error) as exc:
            raise self._unavailable(exc) from exc

    def list_tool_events(self, **filters: Any) -> tuple[list[dict[str, Any]], int]:
        try:
            return self.repository.list_tool_events(**filters)
        except (OSError, sqlite3.Error) as exc:
            raise self._unavailable(exc) from exc

    def stats(self) -> dict[str, int]:
        try:
            return self.repository.stats()
        except (OSError, sqlite3.Error) as exc:
            raise self._unavailable(exc) from exc

    def projects(self) -> list[dict[str, str | int | None]]:
        try:
            return self.repository.projects()
        except (OSError, sqlite3.Error) as exc:
            raise self._unavailable(exc) from exc

    @staticmethod
    def _unavailable(exc: BaseException) -> AppException:
        return AppException(
            code="PROMPT_HISTORY_UNAVAILABLE",
            message="Prompt 历史数据库暂时不可用",
            status_code=503,
            details={"errorType": type(exc).__name__},
        )
