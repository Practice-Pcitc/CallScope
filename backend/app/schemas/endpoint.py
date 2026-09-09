from datetime import datetime
from typing import Any

from app.schemas.common import ApiModel, PaginationMeta


class EndpointData(ApiModel):
    id: str
    project_id: str
    scan_revision_id: str
    http_method: str
    path: str
    function_name: str
    qualified_name: str
    module_name: str
    file_path: str
    start_line: int
    end_line: int
    summary: str | None
    tags: list[str]
    parameters: list[dict[str, Any]]
    response_type: str | None
    dependencies: list[dict[str, Any]]
    metadata: dict[str, Any]
    created_at: datetime

    @classmethod
    def from_entity(cls, endpoint) -> "EndpointData":
        return cls(
            id=endpoint.id,
            project_id=endpoint.project_id,
            scan_revision_id=endpoint.scan_revision_id,
            http_method=endpoint.http_method,
            path=endpoint.path,
            function_name=endpoint.function_name,
            qualified_name=endpoint.qualified_name,
            module_name=endpoint.module_name,
            file_path=endpoint.file_path,
            start_line=endpoint.start_line,
            end_line=endpoint.end_line,
            summary=endpoint.summary,
            tags=endpoint.tags,
            parameters=endpoint.parameters,
            response_type=endpoint.response_type,
            dependencies=endpoint.dependencies,
            metadata=endpoint.extra_metadata,
            created_at=endpoint.created_at,
        )


class EndpointResponse(ApiModel):
    data: EndpointData


class EndpointListData(ApiModel):
    items: list[EndpointData]
    modules: list[str]
    pagination: PaginationMeta


class EndpointListResponse(ApiModel):
    data: EndpointListData
