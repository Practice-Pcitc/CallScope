from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.prompt_history_database import prompt_history_connection
from app.main import app


def _insert_prompt(**overrides) -> str:
    record_id = overrides.pop("id", str(uuid4()))
    values = {
        "id": record_id,
        "session_id": "session-1",
        "turn_id": "turn-1",
        "project_id": "project-1",
        "project_name": "order-system",
        "working_directory": "D:/projects/order-system",
        "repository_path": "D:/projects/order-system",
        "prompt": "帮我分析订单创建接口",
        "prompt_length": 10,
        "source": "codex_user_prompt_submit",
        "model": "test-model",
        "permission_mode": "default",
        "git_branch": "main",
        "git_commit": "abc123",
        "endpoint_ids": json.dumps([]),
        "node_ids": json.dumps([]),
        "created_at": datetime.now(UTC).isoformat(),
    }
    values.update(overrides)
    with prompt_history_connection() as connection:
        connection.execute(
            """
            INSERT INTO prompt_records (
                id, session_id, turn_id, project_id, project_name,
                working_directory, repository_path, prompt, prompt_length,
                source, model, permission_mode, git_branch, git_commit,
                endpoint_ids, node_ids, created_at
            ) VALUES (
                :id, :session_id, :turn_id, :project_id, :project_name,
                :working_directory, :repository_path, :prompt, :prompt_length,
                :source, :model, :permission_mode, :git_branch, :git_commit,
                :endpoint_ids, :node_ids, :created_at
            )
            """,
            values,
        )
    return record_id


def _insert_lifecycle_records() -> None:
    now = datetime.now(UTC).isoformat()
    with prompt_history_connection() as connection:
        connection.execute(
            """
            INSERT INTO codex_sessions (
                session_id, project_id, project_name, working_directory,
                repository_path, model, permission_mode, git_branch, git_commit,
                started_at, ended_at, end_reason, status, prompt_count,
                tool_call_count, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "session-lifecycle",
                "project-1",
                "order-system",
                "D:/projects/order-system",
                "D:/projects/order-system",
                "test-model",
                "default",
                "main",
                "abc123",
                now,
                now,
                "user_exit",
                "ended",
                2,
                1,
                now,
            ),
        )
        connection.execute(
            """
            INSERT INTO codex_tool_events (
                id, session_id, turn_id, project_id, project_name,
                working_directory, tool_name, tool_use_id, status,
                duration_ms, error_type, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                "session-lifecycle",
                "turn-1",
                "project-1",
                "order-system",
                "D:/projects/order-system",
                "shell_command",
                "tool-1",
                "success",
                42.5,
                None,
                now,
            ),
        )


def test_prompt_history_list_detail_search_and_stats() -> None:
    with TestClient(app) as client:
        record_id = _insert_prompt()

        list_response = client.get("/api/prompt-history", params={"keyword": "订单"})
        assert list_response.status_code == 200
        payload = list_response.json()["data"]
        assert payload["pagination"]["total"] == 1
        assert payload["items"][0]["prompt"] == "帮我分析订单创建接口"

        detail_response = client.get(f"/api/prompt-history/{record_id}")
        assert detail_response.status_code == 200
        assert detail_response.json()["data"]["gitBranch"] == "main"

        stats_response = client.get("/api/prompt-history/stats")
        assert stats_response.status_code == 200
        assert stats_response.json()["data"]["totalPromptCount"] == 1


def test_prompt_history_missing_record() -> None:
    with TestClient(app) as client:
        response = client.get("/api/prompt-history/missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROMPT_RECORD_NOT_FOUND"


def test_lifecycle_session_and_tool_event_lists() -> None:
    with TestClient(app) as client:
        _insert_lifecycle_records()

        sessions_response = client.get(
            "/api/prompt-history/sessions",
            params={"sessionId": "session-lifecycle"},
        )
        assert sessions_response.status_code == 200
        sessions = sessions_response.json()["data"]
        assert sessions["pagination"]["total"] == 1
        assert sessions["items"][0]["status"] == "ended"
        assert sessions["items"][0]["toolCallCount"] == 1

        tools_response = client.get(
            "/api/prompt-history/tool-events",
            params={"toolName": "shell", "status": "success"},
        )
        assert tools_response.status_code == 200
        tools = tools_response.json()["data"]
        assert tools["pagination"]["total"] == 1
        assert tools["items"][0]["toolName"] == "shell_command"
        assert tools["items"][0]["durationMs"] == 42.5
