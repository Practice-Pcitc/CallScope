from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import PaginationMeta
from app.schemas.project import (
    ProjectCreate,
    ProjectData,
    ProjectListData,
    ProjectListResponse,
    ProjectResponse,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects")


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="导入本地项目",
)
def create_project(
    payload: ProjectCreate,
    session: Annotated[Session, Depends(get_db)],
) -> ProjectResponse:
    project = ProjectService(session).create(payload)
    return ProjectResponse(data=ProjectData.from_entity(project))


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="查询项目列表",
)
def list_projects(
    session: Annotated[Session, Depends(get_db)],
    search: Annotated[str | None, Query(max_length=120)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> ProjectListResponse:
    items, total = ProjectService(session).list(
        search=search,
        page=page,
        page_size=page_size,
    )
    return ProjectListResponse(
        data=ProjectListData(
            items=[ProjectData.from_entity(item) for item in items],
            pagination=PaginationMeta(page=page, page_size=page_size, total=total),
        )
    )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="查询项目详情",
)
def get_project(
    project_id: str,
    session: Annotated[Session, Depends(get_db)],
) -> ProjectResponse:
    project = ProjectService(session).get(project_id)
    return ProjectResponse(data=ProjectData.from_entity(project))


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除项目记录",
)
def delete_project(
    project_id: str,
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    ProjectService(session).delete(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

