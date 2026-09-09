from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import PaginationMeta
from app.schemas.endpoint import (
    EndpointData,
    EndpointListData,
    EndpointListResponse,
    EndpointResponse,
)
from app.services.endpoint_service import EndpointService

router = APIRouter(prefix="/projects")


@router.get(
    "/{project_id}/endpoints",
    response_model=EndpointListResponse,
    summary="查询项目接口列表",
)
def list_endpoints(
    project_id: str,
    session: Annotated[Session, Depends(get_db)],
    search: Annotated[str | None, Query(max_length=255)] = None,
    http_method: Annotated[str | None, Query(alias="httpMethod", max_length=12)] = None,
    module: Annotated[str | None, Query(max_length=512)] = None,
    tag: Annotated[str | None, Query(max_length=255)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=200)] = 100,
) -> EndpointListResponse:
    items, modules, total = EndpointService(session).list(
        project_id=project_id,
        search=search,
        http_method=http_method,
        module=module,
        tag=tag,
        page=page,
        page_size=page_size,
    )
    return EndpointListResponse(
        data=EndpointListData(
            items=[EndpointData.from_entity(item) for item in items],
            modules=modules,
            pagination=PaginationMeta(page=page, page_size=page_size, total=total),
        )
    )


@router.get(
    "/{project_id}/endpoints/{endpoint_id}",
    response_model=EndpointResponse,
    summary="查询接口详情",
)
def get_endpoint(
    project_id: str,
    endpoint_id: str,
    session: Annotated[Session, Depends(get_db)],
) -> EndpointResponse:
    endpoint = EndpointService(session).get(
        project_id=project_id,
        endpoint_id=endpoint_id,
    )
    return EndpointResponse(data=EndpointData.from_entity(endpoint))
