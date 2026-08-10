from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from uuid import uuid4

from config import HookConfig
from git_metadata import read_git_metadata
from logger import build_logger
from models import PromptRecord, SessionRecord, ToolEventRecord
from project_resolver import resolve_project
from redaction import redact_prompt
from storage import PromptStorage

SUPPORTED_EVENTS = {
    "SessionStart",
    "UserPromptSubmit",
    "PostToolUse",
    "SessionEnd",
}


def _optional_text(payload: dict[str, object], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _optional_number(payload: dict[str, object], *keys: str) -> float | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return None


def _tool_status(payload: dict[str, object]) -> tuple[str, str | None]:
    error = payload.get("error")
    response = payload.get("tool_response", payload.get("tool_result"))
    if error:
        error_type = _optional_text(error, "type", "name") if isinstance(error, dict) else None
        return "failed", error_type or "ToolError"
    if isinstance(response, dict) and response.get("is_error") is True:
        return "failed", _optional_text(response, "error_type", "type") or "ToolError"
    return "success", None


def _session_record(
    payload: dict[str, object],
    *,
    config: HookConfig,
    created_at: str,
) -> tuple[SessionRecord | None, object, object]:
    cwd = _optional_text(payload, "cwd", "working_directory") or os.getcwd()
    git = read_git_metadata(cwd)
    project = resolve_project(
        working_directory=cwd,
        project_database_path=config.project_database_path,
        git=git,
    )
    session_id = _optional_text(payload, "session_id", "conversation_id", "thread_id")
    if not session_id:
        return None, git, project
    return (
        SessionRecord(
            session_id=session_id,
            project_id=project.project_id,
            project_name=project.project_name,
            working_directory=cwd,
            repository_path=git.repository_path,
            model=_optional_text(payload, "model"),
            permission_mode=_optional_text(payload, "permission_mode", "approval_policy"),
            git_branch=git.branch,
            git_commit=git.commit,
            started_at=created_at,
        ),
        git,
        project,
    )


def handle(payload: dict[str, object], config: HookConfig) -> str | None:
    event_name = _optional_text(payload, "hook_event_name")
    if not config.enabled or event_name not in SUPPORTED_EVENTS:
        return None

    created_at = datetime.now(UTC).isoformat()
    session, git, project = _session_record(
        payload,
        config=config,
        created_at=created_at,
    )
    cwd = session.working_directory if session else (
        _optional_text(payload, "cwd", "working_directory") or os.getcwd()
    )
    session_id = session.session_id if session else None
    storage = PromptStorage(
        config.database_path,
        timeout_seconds=config.sqlite_timeout_seconds,
    )
    if session:
        storage.start_session(session)

    if event_name == "SessionStart":
        return session_id

    if event_name == "UserPromptSubmit":
        prompt = payload.get("prompt")
        if not isinstance(prompt, str):
            return None
        stored_prompt = redact_prompt(prompt) if config.redaction_enabled else prompt
        record = PromptRecord(
            id=str(uuid4()),
            session_id=session_id,
            turn_id=_optional_text(payload, "turn_id"),
            project_id=project.project_id,
            project_name=project.project_name,
            working_directory=cwd,
            repository_path=git.repository_path,
            prompt=stored_prompt,
            prompt_length=len(prompt),
            source="codex_user_prompt_submit",
            model=_optional_text(payload, "model"),
            permission_mode=_optional_text(payload, "permission_mode", "approval_policy"),
            git_branch=git.branch,
            git_commit=git.commit,
            endpoint_ids="[]",
            node_ids="[]",
            created_at=created_at,
        )
        storage.insert(record)
        storage.increment_session_counter(
            session_id,
            counter="prompt_count",
            updated_at=created_at,
        )
        return record.id

    if event_name == "PostToolUse":
        status, error_type = _tool_status(payload)
        record = ToolEventRecord(
            id=str(uuid4()),
            session_id=session_id,
            turn_id=_optional_text(payload, "turn_id"),
            project_id=project.project_id,
            project_name=project.project_name,
            working_directory=cwd,
            tool_name=_optional_text(payload, "tool_name", "tool", "name") or "unknown",
            tool_use_id=_optional_text(payload, "tool_use_id", "call_id", "tool_call_id"),
            status=status,
            duration_ms=_optional_number(payload, "duration_ms", "elapsed_ms"),
            error_type=error_type,
            created_at=created_at,
        )
        storage.insert_tool_event(record)
        storage.increment_session_counter(
            session_id,
            counter="tool_call_count",
            updated_at=created_at,
        )
        return record.id

    if event_name == "SessionEnd" and session_id:
        storage.end_session(
            session_id,
            ended_at=created_at,
            reason=_optional_text(payload, "reason", "end_reason", "source"),
        )
        return session_id
    return None


def main() -> int:
    logger = None
    try:
        config = HookConfig.load()
        logger = build_logger(config.log_path)
        raw = sys.stdin.read()
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            return 0
        record_id = handle(payload, config)
        if record_id:
            logger.info("hook_saved event=%s id=%s", payload.get("hook_event_name"), record_id)
    except Exception as exc:  # noqa: BLE001 - an audit hook must fail open.
        if logger is not None:
            logger.error("hook_save_failed error=%s", type(exc).__name__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
