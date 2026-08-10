from __future__ import annotations

from datetime import datetime

from app.schemas.common import ApiModel, PaginationMeta


class PromptRecordData(ApiModel):
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
    endpoint_ids: list[str]
    node_ids: list[str]
    created_at: datetime


class PromptRecordResponse(ApiModel):
    data: PromptRecordData


class PromptHistoryListData(ApiModel):
    items: list[PromptRecordData]
    pagination: PaginationMeta


class PromptHistoryListResponse(ApiModel):
    data: PromptHistoryListData


class PromptStatsData(ApiModel):
    total_prompt_count: int
    today_prompt_count: int
    project_count: int
    recent_prompt_count: int
    recent_days: int = 7


class PromptStatsResponse(ApiModel):
    data: PromptStatsData


class PromptProjectData(ApiModel):
    project_id: str | None
    project_name: str
    prompt_count: int
    last_prompt_at: datetime


class PromptProjectListResponse(ApiModel):
    data: list[PromptProjectData]


class CodexSessionData(ApiModel):
    session_id: str
    project_id: str | None
    project_name: str
    working_directory: str
    repository_path: str | None
    model: str | None
    permission_mode: str | None
    git_branch: str | None
    git_commit: str | None
    started_at: datetime
    ended_at: datetime | None
    end_reason: str | None
    status: str
    prompt_count: int
    tool_call_count: int
    updated_at: datetime


class CodexSessionListData(ApiModel):
    items: list[CodexSessionData]
    pagination: PaginationMeta


class CodexSessionListResponse(ApiModel):
    data: CodexSessionListData


class ToolEventData(ApiModel):
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
    created_at: datetime


class ToolEventListData(ApiModel):
    items: list[ToolEventData]
    pagination: PaginationMeta


class ToolEventListResponse(ApiModel):
    data: ToolEventListData
