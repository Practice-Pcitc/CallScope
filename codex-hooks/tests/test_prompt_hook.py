from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

HOOK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOK_ROOT))

from config import HookConfig
from prompt_hook import handle


def test_hook_saves_prompt_and_matches_project(tmp_path: Path) -> None:
    project_root = tmp_path / "sample-project"
    project_root.mkdir()
    child = project_root / "src"
    child.mkdir()

    project_database = tmp_path / "callscope.db"
    with sqlite3.connect(project_database) as connection:
        connection.execute("CREATE TABLE projects (id TEXT, name TEXT, root_path TEXT)")
        connection.execute(
            "INSERT INTO projects VALUES (?, ?, ?)",
            ("project-1", "Sample", str(project_root)),
        )

    prompt_database = tmp_path / "prompt_history.db"
    config = HookConfig(
        enabled=True,
        redaction_enabled=False,
        database_path=prompt_database,
        project_database_path=project_database,
        log_path=tmp_path / "hook.log",
    )
    record_id = handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "session-1",
            "turn_id": "turn-1",
            "cwd": str(child),
            "prompt": "分析订单接口\n保留原格式",
            "model": "test-model",
            "permission_mode": "default",
        },
        config,
    )

    assert record_id
    with sqlite3.connect(prompt_database) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute("SELECT * FROM prompt_records").fetchone()
    assert row is not None
    assert row["project_id"] == "project-1"
    assert row["project_name"] == "Sample"
    assert row["prompt"] == "分析订单接口\n保留原格式"
    assert json.loads(row["endpoint_ids"]) == []


def test_hook_redacts_only_stored_copy(tmp_path: Path) -> None:
    prompt = "Bearer abcdefghijklmnop password=hunter2"
    config = HookConfig(
        enabled=True,
        redaction_enabled=True,
        database_path=tmp_path / "prompt_history.db",
        project_database_path=tmp_path / "missing.db",
        log_path=tmp_path / "hook.log",
    )
    handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "cwd": str(tmp_path),
            "prompt": prompt,
        },
        config,
    )

    with sqlite3.connect(config.database_path) as connection:
        stored = connection.execute("SELECT prompt FROM prompt_records").fetchone()[0]
    assert stored != prompt
    assert "hunter2" not in stored
    assert "abcdefghijklmnop" not in stored


def test_lifecycle_hooks_track_session_and_tool_usage(tmp_path: Path) -> None:
    config = HookConfig(
        enabled=True,
        redaction_enabled=False,
        database_path=tmp_path / "prompt_history.db",
        project_database_path=tmp_path / "missing.db",
        log_path=tmp_path / "hook.log",
    )
    common = {
        "session_id": "session-lifecycle",
        "cwd": str(tmp_path),
        "model": "test-model",
    }

    assert handle({**common, "hook_event_name": "SessionStart"}, config)
    assert handle(
        {
            **common,
            "hook_event_name": "UserPromptSubmit",
            "turn_id": "turn-1",
            "prompt": "分析这个项目",
        },
        config,
    )
    assert handle(
        {
            **common,
            "hook_event_name": "PostToolUse",
            "turn_id": "turn-1",
            "tool_name": "shell_command",
            "tool_use_id": "tool-1",
            "duration_ms": 12.5,
            "tool_response": {"is_error": False, "content": "must not be stored"},
        },
        config,
    )
    assert handle(
        {
            **common,
            "hook_event_name": "SessionEnd",
            "reason": "user_exit",
        },
        config,
    )

    with sqlite3.connect(config.database_path) as connection:
        connection.row_factory = sqlite3.Row
        session = connection.execute(
            "SELECT * FROM codex_sessions WHERE session_id = ?",
            ("session-lifecycle",),
        ).fetchone()
        tool = connection.execute("SELECT * FROM codex_tool_events").fetchone()

    assert session is not None
    assert session["status"] == "ended"
    assert session["end_reason"] == "user_exit"
    assert session["prompt_count"] == 1
    assert session["tool_call_count"] == 1
    assert tool is not None
    assert tool["tool_name"] == "shell_command"
    assert tool["status"] == "success"
    assert "must not be stored" not in str(dict(tool))


def test_failed_tool_hook_records_only_error_type(tmp_path: Path) -> None:
    config = HookConfig(
        enabled=True,
        redaction_enabled=False,
        database_path=tmp_path / "prompt_history.db",
        project_database_path=tmp_path / "missing.db",
        log_path=tmp_path / "hook.log",
    )
    handle(
        {
            "hook_event_name": "PostToolUse",
            "cwd": str(tmp_path),
            "tool_name": "shell_command",
            "error": "secret failure details",
        },
        config,
    )

    with sqlite3.connect(config.database_path) as connection:
        row = connection.execute(
            "SELECT status, error_type FROM codex_tool_events"
        ).fetchone()
    assert row == ("failed", "ToolError")
