from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import PaginationMeta
from app.schemas.prompt_history import (
    CodexSessionData,
    CodexSessionListData,
    CodexSessionListResponse,
    PromptHistoryListData,
    PromptHistoryListResponse,
    PromptProjectData,
    PromptProjectListResponse,
    PromptRecordData,
    PromptRecordResponse,
    PromptStatsData,
    PromptStatsResponse,
    ToolEventData,
    ToolEventListData,
    ToolEventListResponse,
)
from app.services.project_service import ProjectService
from app.services.prompt_history_service import PromptHistoryService

router = APIRouter()


def _list_response(
    *,
    page: int,
    page_size: int,
    project_id: str | None,
    project_name: str | None,
    keyword: str | None,
    session_id: str | None,
    start_time: datetime | None,
    end_time: datetime | None,
) -> PromptHistoryListResponse:
    items, total = PromptHistoryService().list(
        page=page,
        page_size=page_size,
        project_id=project_id,
        project_name=project_name,
        keyword=keyword,
        session_id=session_id,
        start_time=start_time,
        end_time=end_time,
    )
    return PromptHistoryListResponse(
        data=PromptHistoryListData(
            items=[PromptRecordData.model_validate(item) for item in items],
            pagination=PaginationMeta(page=page, page_size=page_size, total=total),
        )
    )


@router.get(
    "/prompt-history/stats",
    response_model=PromptStatsResponse,
    summary="查询 Prompt 历史统计",
)
def prompt_history_stats() -> PromptStatsResponse:
    stats = PromptHistoryService().stats()
    return PromptStatsResponse(
        data=PromptStatsData(
            total_prompt_count=stats["total"],
            today_prompt_count=stats["today"],
            project_count=stats["projects"],
            recent_prompt_count=stats["recent"],
        )
    )


@router.get(
    "/prompt-history/projects",
    response_model=PromptProjectListResponse,
    summary="查询包含 Prompt 的项目",
)
def prompt_history_projects() -> PromptProjectListResponse:
    return PromptProjectListResponse(
        data=[
            PromptProjectData.model_validate(item)
            for item in PromptHistoryService().projects()
        ]
    )


@router.get(
    "/prompt-history/sessions",
    response_model=CodexSessionListResponse,
    summary="分页查询 Codex 会话",
)
def list_codex_sessions(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    project_id: Annotated[str | None, Query(alias="projectId")] = None,
    project_name: Annotated[str | None, Query(alias="projectName", max_length=120)] = None,
    session_id: Annotated[str | None, Query(alias="sessionId", max_length=200)] = None,
    status: Annotated[str | None, Query(pattern="^(active|ended)$")] = None,
    start_time: Annotated[datetime | None, Query(alias="startTime")] = None,
    end_time: Annotated[datetime | None, Query(alias="endTime")] = None,
) -> CodexSessionListResponse:
    items, total = PromptHistoryService().list_sessions(
        page=page,
        page_size=page_size,
        project_id=project_id,
        project_name=project_name,
        session_id=session_id,
        status=status,
        start_time=start_time,
        end_time=end_time,
    )
    return CodexSessionListResponse(
        data=CodexSessionListData(
            items=[CodexSessionData.model_validate(item) for item in items],
            pagination=PaginationMeta(page=page, page_size=page_size, total=total),
        )
    )


@router.get(
    "/prompt-history/tool-events",
    response_model=ToolEventListResponse,
    summary="分页查询 Codex 工具调用",
)
def list_tool_events(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    project_id: Annotated[str | None, Query(alias="projectId")] = None,
    project_name: Annotated[str | None, Query(alias="projectName", max_length=120)] = None,
    session_id: Annotated[str | None, Query(alias="sessionId", max_length=200)] = None,
    tool_name: Annotated[str | None, Query(alias="toolName", max_length=200)] = None,
    status: Annotated[str | None, Query(pattern="^(success|failed)$")] = None,
    start_time: Annotated[datetime | None, Query(alias="startTime")] = None,
    end_time: Annotated[datetime | None, Query(alias="endTime")] = None,
) -> ToolEventListResponse:
    items, total = PromptHistoryService().list_tool_events(
        page=page,
        page_size=page_size,
        project_id=project_id,
        project_name=project_name,
        session_id=session_id,
        tool_name=tool_name,
        status=status,
        start_time=start_time,
        end_time=end_time,
    )
    return ToolEventListResponse(
        data=ToolEventListData(
            items=[ToolEventData.model_validate(item) for item in items],
            pagination=PaginationMeta(page=page, page_size=page_size, total=total),
        )
    )


@router.get(
    "/prompt-history",
    response_model=PromptHistoryListResponse,
    summary="分页查询 Prompt 历史",
)
def list_prompt_history(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    project_id: Annotated[str | None, Query(alias="projectId")] = None,
    project_name: Annotated[str | None, Query(alias="projectName", max_length=120)] = None,
    keyword: Annotated[str | None, Query(max_length=500)] = None,
    session_id: Annotated[str | None, Query(alias="sessionId", max_length=200)] = None,
    start_time: Annotated[datetime | None, Query(alias="startTime")] = None,
    end_time: Annotated[datetime | None, Query(alias="endTime")] = None,
) -> PromptHistoryListResponse:
    return _list_response(
        page=page,
        page_size=page_size,
        project_id=project_id,
        project_name=project_name,
        keyword=keyword,
        session_id=session_id,
        start_time=start_time,
        end_time=end_time,
    )


@router.get(
    "/prompt-history/{record_id}",
    response_model=PromptRecordResponse,
    summary="查询单条 Prompt 详情",
)
def get_prompt_history(record_id: str) -> PromptRecordResponse:
    return PromptRecordResponse(
        data=PromptRecordData.model_validate(PromptHistoryService().get(record_id))
    )


@router.get(
    "/projects/{project_id}/prompt-history",
    response_model=PromptHistoryListResponse,
    summary="查询项目 Prompt 历史",
)
def list_project_prompt_history(
    project_id: str,
    session: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    keyword: Annotated[str | None, Query(max_length=500)] = None,
    session_id: Annotated[str | None, Query(alias="sessionId", max_length=200)] = None,
    start_time: Annotated[datetime | None, Query(alias="startTime")] = None,
    end_time: Annotated[datetime | None, Query(alias="endTime")] = None,
) -> PromptHistoryListResponse:
    ProjectService(session).get(project_id)
    return _list_response(
        page=page,
        page_size=page_size,
        project_id=project_id,
        project_name=None,
        keyword=keyword,
        session_id=session_id,
        start_time=start_time,
        end_time=end_time,
    )
