from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProjectMatch:
    project_id: str | None
    project_name: str


@dataclass(frozen=True, slots=True)
class GitMetadata:
    repository_path: str | None = None
    branch: str | None = None
    commit: str | None = None


@dataclass(frozen=True, slots=True)
class PromptRecord:
    id: str
    session_id: str | None
    turn_id: str | None
    project_id: str | None
    project_name: str
    working_directory: str
    repository_path: str | None
    prompt: str
    prompt_length: int
    source: str
    model: str | None
    permission_mode: str | None
    git_branch: str | None
    git_commit: str | None
    endpoint_ids: str
    node_ids: str
    created_at: str


@dataclass(frozen=True, slots=True)
class SessionRecord:
    session_id: str
    project_id: str | None
    project_name: str
    working_directory: str
    repository_path: str | None
    model: str | None
    permission_mode: str | None
    git_branch: str | None
    git_commit: str | None
    started_at: str


@dataclass(frozen=True, slots=True)
class ToolEventRecord:
    id: str
    session_id: str | None
    turn_id: str | None
    project_id: str | None
    project_name: str
    working_directory: str
    tool_name: str
    tool_use_id: str | None
    status: str
    duration_ms: float | None
    error_type: str | None
    created_at: str
