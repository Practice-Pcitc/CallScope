from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.prompt_history_database import (
    PROMPT_HISTORY_SCHEMA,
    prompt_history_connection,
)


def _decode_ids(value: str | None) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _serialize(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["endpoint_ids"] = _decode_ids(item.get("endpoint_ids"))
    item["node_ids"] = _decode_ids(item.get("node_ids"))
    return item


class PromptHistoryRepository:
    def _ensure_schema(self, connection: sqlite3.Connection) -> None:
        connection.executescript(PROMPT_HISTORY_SCHEMA)

    def list(
        self,
        *,
        page: int,
        page_size: int,
        project_id: str | None = None,
        project_name: str | None = None,
        keyword: str | None = None,
        session_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        clauses: list[str] = []
        parameters: list[object] = []

        if project_id:
            clauses.append("project_id = ?")
            parameters.append(project_id)
        if project_name:
            clauses.append("LOWER(project_name) = LOWER(?)")
            parameters.append(project_name.strip())
        if keyword:
            clauses.append("LOWER(prompt) LIKE LOWER(?) ESCAPE '\\'")
            escaped = keyword.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            parameters.append(f"%{escaped}%")
        if session_id:
            clauses.append("session_id = ?")
            parameters.append(session_id.strip())
        if start_time:
            clauses.append("created_at >= ?")
            parameters.append(start_time.astimezone(UTC).isoformat())
        if end_time:
            clauses.append("created_at <= ?")
            parameters.append(end_time.astimezone(UTC).isoformat())

        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with prompt_history_connection() as connection:
            self._ensure_schema(connection)
            total = connection.execute(
                f"SELECT COUNT(*) FROM prompt_records{where}",  # noqa: S608
                parameters,
            ).fetchone()[0]
            rows = connection.execute(
                f"""
                SELECT * FROM prompt_records{where}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,  # noqa: S608
                [*parameters, page_size, (page - 1) * page_size],
            ).fetchall()
        return [_serialize(row) for row in rows], int(total)

    def get(self, record_id: str) -> dict[str, Any] | None:
        with prompt_history_connection() as connection:
            self._ensure_schema(connection)
            row = connection.execute(
                "SELECT * FROM prompt_records WHERE id = ?", (record_id,)
            ).fetchone()
        return _serialize(row) if row else None

    def list_sessions(
        self,
        *,
        page: int,
        page_size: int,
        project_id: str | None = None,
        session_id: str | None = None,
        status: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        clauses: list[str] = []
        parameters: list[object] = []
        if project_id:
            clauses.append("project_id = ?")
            parameters.append(project_id)
        if session_id:
            clauses.append("session_id = ?")
            parameters.append(session_id.strip())
        if status:
            clauses.append("status = ?")
            parameters.append(status)
        if start_time:
            clauses.append("started_at >= ?")
            parameters.append(start_time.astimezone(UTC).isoformat())
        if end_time:
            clauses.append("started_at <= ?")
            parameters.append(end_time.astimezone(UTC).isoformat())
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with prompt_history_connection() as connection:
            self._ensure_schema(connection)
            total = connection.execute(
                f"SELECT COUNT(*) FROM codex_sessions{where}",  # noqa: S608
                parameters,
            ).fetchone()[0]
            rows = connection.execute(
                f"""
                SELECT * FROM codex_sessions{where}
                ORDER BY started_at DESC
                LIMIT ? OFFSET ?
                """,  # noqa: S608
                [*parameters, page_size, (page - 1) * page_size],
            ).fetchall()
        return [dict(row) for row in rows], int(total)

    def list_tool_events(
        self,
        *,
        page: int,
        page_size: int,
        project_id: str | None = None,
        session_id: str | None = None,
        tool_name: str | None = None,
        status: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        clauses: list[str] = []
        parameters: list[object] = []
        if project_id:
            clauses.append("project_id = ?")
            parameters.append(project_id)
        if session_id:
            clauses.append("session_id = ?")
            parameters.append(session_id.strip())
        if tool_name:
            clauses.append("LOWER(tool_name) LIKE LOWER(?)")
            parameters.append(f"%{tool_name.strip()}%")
        if status:
            clauses.append("status = ?")
            parameters.append(status)
        if start_time:
            clauses.append("created_at >= ?")
            parameters.append(start_time.astimezone(UTC).isoformat())
        if end_time:
            clauses.append("created_at <= ?")
            parameters.append(end_time.astimezone(UTC).isoformat())
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with prompt_history_connection() as connection:
            self._ensure_schema(connection)
            total = connection.execute(
                f"SELECT COUNT(*) FROM codex_tool_events{where}",  # noqa: S608
                parameters,
            ).fetchone()[0]
            rows = connection.execute(
                f"""
                SELECT * FROM codex_tool_events{where}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,  # noqa: S608
                [*parameters, page_size, (page - 1) * page_size],
            ).fetchall()
        return [dict(row) for row in rows], int(total)

    def stats(self) -> dict[str, int]:
        now = datetime.now(UTC)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        recent = (now - timedelta(days=7)).isoformat()
        with prompt_history_connection() as connection:
            self._ensure_schema(connection)
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END) AS today,
                    COUNT(DISTINCT CASE
                        WHEN project_id IS NOT NULL THEN project_id
                        ELSE project_name
                    END) AS projects,
                    SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END) AS recent
                FROM prompt_records
                """,
                (today, recent),
            ).fetchone()
        return {
            "total": int(row["total"] or 0),
            "today": int(row["today"] or 0),
            "projects": int(row["projects"] or 0),
            "recent": int(row["recent"] or 0),
        }

    def projects(self) -> list[dict[str, str | None]]:
        with prompt_history_connection() as connection:
            self._ensure_schema(connection)
            rows = connection.execute(
                """
                SELECT project_id, project_name, COUNT(*) AS prompt_count,
                       MAX(created_at) AS last_prompt_at
                FROM prompt_records
                GROUP BY project_id, project_name
                ORDER BY last_prompt_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]
