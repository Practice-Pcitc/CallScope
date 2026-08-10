from __future__ import annotations

import sqlite3
from pathlib import Path

from models import PromptRecord, SessionRecord, ToolEventRecord

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS prompt_records (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    turn_id TEXT,
    project_id TEXT,
    project_name TEXT NOT NULL,
    working_directory TEXT NOT NULL,
    repository_path TEXT,
    prompt TEXT NOT NULL,
    prompt_length INTEGER NOT NULL,
    source TEXT NOT NULL,
    model TEXT,
    permission_mode TEXT,
    git_branch TEXT,
    git_commit TEXT,
    endpoint_ids TEXT NOT NULL DEFAULT '[]',
    node_ids TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_prompt_records_created_at
    ON prompt_records(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_prompt_records_project_name
    ON prompt_records(project_name);
CREATE INDEX IF NOT EXISTS ix_prompt_records_project_id
    ON prompt_records(project_id);
CREATE INDEX IF NOT EXISTS ix_prompt_records_session_id
    ON prompt_records(session_id);
CREATE TABLE IF NOT EXISTS codex_sessions (
    session_id TEXT PRIMARY KEY,
    project_id TEXT,
    project_name TEXT NOT NULL,
    working_directory TEXT NOT NULL,
    repository_path TEXT,
    model TEXT,
    permission_mode TEXT,
    git_branch TEXT,
    git_commit TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    end_reason TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    prompt_count INTEGER NOT NULL DEFAULT 0,
    tool_call_count INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_codex_sessions_started_at
    ON codex_sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS ix_codex_sessions_project_id
    ON codex_sessions(project_id);
CREATE TABLE IF NOT EXISTS codex_tool_events (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    turn_id TEXT,
    project_id TEXT,
    project_name TEXT NOT NULL,
    working_directory TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    tool_use_id TEXT,
    status TEXT NOT NULL,
    duration_ms REAL,
    error_type TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_codex_tool_events_created_at
    ON codex_tool_events(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_codex_tool_events_session_id
    ON codex_tool_events(session_id);
CREATE INDEX IF NOT EXISTS ix_codex_tool_events_tool_name
    ON codex_tool_events(tool_name);
"""


class PromptStorage:
    def __init__(self, database_path: Path, *, timeout_seconds: float = 0.2) -> None:
        self.database_path = database_path
        self.timeout_seconds = timeout_seconds

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            self.database_path,
            timeout=self.timeout_seconds,
        )
        connection.execute("PRAGMA busy_timeout=200")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(SCHEMA_SQL)

    def insert(self, record: PromptRecord) -> None:
        with self._connect() as connection:
            connection.executescript(SCHEMA_SQL)
            connection.execute(
                """
                INSERT INTO prompt_records (
                    id, session_id, turn_id, project_id, project_name,
                    working_directory, repository_path, prompt, prompt_length,
                    source, model, permission_mode, git_branch, git_commit,
                    endpoint_ids, node_ids, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.session_id,
                    record.turn_id,
                    record.project_id,
                    record.project_name,
                    record.working_directory,
                    record.repository_path,
                    record.prompt,
                    record.prompt_length,
                    record.source,
                    record.model,
                    record.permission_mode,
                    record.git_branch,
                    record.git_commit,
                    record.endpoint_ids,
                    record.node_ids,
                    record.created_at,
                ),
            )

    def start_session(self, record: SessionRecord) -> None:
        with self._connect() as connection:
            connection.executescript(SCHEMA_SQL)
            connection.execute(
                """
                INSERT INTO codex_sessions (
                    session_id, project_id, project_name, working_directory,
                    repository_path, model, permission_mode, git_branch,
                    git_commit, started_at, status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    project_id = COALESCE(excluded.project_id, codex_sessions.project_id),
                    project_name = excluded.project_name,
                    working_directory = excluded.working_directory,
                    repository_path = COALESCE(
                        excluded.repository_path, codex_sessions.repository_path
                    ),
                    model = COALESCE(excluded.model, codex_sessions.model),
                    permission_mode = COALESCE(
                        excluded.permission_mode, codex_sessions.permission_mode
                    ),
                    git_branch = COALESCE(excluded.git_branch, codex_sessions.git_branch),
                    git_commit = COALESCE(excluded.git_commit, codex_sessions.git_commit),
                    status = CASE
                        WHEN codex_sessions.status = 'ended' THEN codex_sessions.status
                        ELSE 'active'
                    END,
                    updated_at = excluded.updated_at
                """,
                (
                    record.session_id,
                    record.project_id,
                    record.project_name,
                    record.working_directory,
                    record.repository_path,
                    record.model,
                    record.permission_mode,
                    record.git_branch,
                    record.git_commit,
                    record.started_at,
                    record.started_at,
                ),
            )

    def increment_session_counter(
        self,
        session_id: str | None,
        *,
        counter: str,
        updated_at: str,
    ) -> None:
        if not session_id:
            return
        if counter not in {"prompt_count", "tool_call_count"}:
            raise ValueError("unsupported session counter")
        with self._connect() as connection:
            connection.executescript(SCHEMA_SQL)
            connection.execute(
                f"""
                UPDATE codex_sessions
                SET {counter} = {counter} + 1, updated_at = ?
                WHERE session_id = ?
                """,
                (updated_at, session_id),
            )

    def insert_tool_event(self, record: ToolEventRecord) -> None:
        with self._connect() as connection:
            connection.executescript(SCHEMA_SQL)
            connection.execute(
                """
                INSERT INTO codex_tool_events (
                    id, session_id, turn_id, project_id, project_name,
                    working_directory, tool_name, tool_use_id, status,
                    duration_ms, error_type, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.session_id,
                    record.turn_id,
                    record.project_id,
                    record.project_name,
                    record.working_directory,
                    record.tool_name,
                    record.tool_use_id,
                    record.status,
                    record.duration_ms,
                    record.error_type,
                    record.created_at,
                ),
            )

    def end_session(
        self,
        session_id: str,
        *,
        ended_at: str,
        reason: str | None,
    ) -> None:
        with self._connect() as connection:
            connection.executescript(SCHEMA_SQL)
            connection.execute(
                """
                UPDATE codex_sessions
                SET ended_at = ?, end_reason = ?, status = 'ended', updated_at = ?
                WHERE session_id = ?
                """,
                (ended_at, reason, ended_at, session_id),
            )
