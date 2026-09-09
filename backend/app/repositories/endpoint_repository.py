from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.api_endpoint import ApiEndpoint


class EndpointRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_many(self, endpoints: list[ApiEndpoint]) -> None:
        self.session.add_all(endpoints)
        self.session.flush()

    def get(self, endpoint_id: str) -> ApiEndpoint | None:
        return self.session.get(ApiEndpoint, endpoint_id)

    def list(
        self,
        *,
        project_id: str,
        revision_id: str,
        search: str | None,
        http_method: str | None,
        module: str | None,
        tag: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[ApiEndpoint], int]:
        conditions = [
            ApiEndpoint.project_id == project_id,
            ApiEndpoint.scan_revision_id == revision_id,
        ]
        if search:
            pattern = f"%{search.strip()}%"
            conditions.append(
                or_(
                    ApiEndpoint.path.ilike(pattern),
                    ApiEndpoint.function_name.ilike(pattern),
                )
            )
        if http_method:
            conditions.append(ApiEndpoint.http_method == http_method.upper())
        if module:
            conditions.append(ApiEndpoint.module_name == module)

        statement = select(ApiEndpoint).where(*conditions)
        if tag:
            all_items = list(
                self.session.scalars(statement.order_by(ApiEndpoint.path, ApiEndpoint.http_method))
            )
            tagged_items = [item for item in all_items if tag in item.tags]
            return tagged_items[offset : offset + limit], len(tagged_items)

        items = list(
            self.session.scalars(
                statement.order_by(ApiEndpoint.path, ApiEndpoint.http_method)
                .offset(offset)
                .limit(limit)
            )
        )
        total = (
            self.session.scalar(select(func.count()).select_from(ApiEndpoint).where(*conditions))
            or 0
        )
        return items, total

    def modules(self, *, project_id: str, revision_id: str) -> list[str]:
        statement = (
            select(ApiEndpoint.module_name)
            .where(
                ApiEndpoint.project_id == project_id,
                ApiEndpoint.scan_revision_id == revision_id,
            )
            .distinct()
            .order_by(ApiEndpoint.module_name)
        )
        return list(self.session.scalars(statement))
