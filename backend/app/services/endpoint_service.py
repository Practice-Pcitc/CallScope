from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.api_endpoint import ApiEndpoint
from app.repositories.endpoint_repository import EndpointRepository
from app.repositories.project_repository import ProjectRepository


class EndpointService:
    def __init__(self, session: Session) -> None:
        self.projects = ProjectRepository(session)
        self.endpoints = EndpointRepository(session)

    def list(
        self,
        *,
        project_id: str,
        search: str | None,
        http_method: str | None,
        module: str | None,
        tag: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[ApiEndpoint], list[str], int]:
        project = self.projects.get(project_id)
        if not project:
            raise AppException(
                code="PROJECT_NOT_FOUND",
                message="项目不存在",
                status_code=404,
            )
        if not project.active_revision_id:
            return [], [], 0
        items, total = self.endpoints.list(
            project_id=project.id,
            revision_id=project.active_revision_id,
            search=search,
            http_method=http_method,
            module=module,
            tag=tag,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        modules = self.endpoints.modules(
            project_id=project.id,
            revision_id=project.active_revision_id,
        )
        return items, modules, total

    def get(self, *, project_id: str, endpoint_id: str) -> ApiEndpoint:
        project = self.projects.get(project_id)
        if not project:
            raise AppException(
                code="PROJECT_NOT_FOUND",
                message="项目不存在",
                status_code=404,
            )
        endpoint = self.endpoints.get(endpoint_id)
        if (
            not endpoint
            or endpoint.project_id != project.id
            or endpoint.scan_revision_id != project.active_revision_id
        ):
            raise AppException(
                code="ENDPOINT_NOT_FOUND",
                message="接口不存在",
                status_code=404,
            )
        return endpoint
