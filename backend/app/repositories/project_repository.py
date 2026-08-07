from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.project import Project


class ProjectRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, project: Project) -> Project:
        self.session.add(project)
        self.session.flush()
        return project

    def get(self, project_id: str) -> Project | None:
        return self.session.get(Project, project_id)

    def get_by_root_path(self, root_path: str) -> Project | None:
        statement = select(Project).where(func.lower(Project.root_path) == root_path.lower())
        return self.session.scalar(statement)

    def list(self, *, search: str | None, offset: int, limit: int) -> tuple[list[Project], int]:
        statement = select(Project)
        count_statement = select(func.count()).select_from(Project)
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(Project.name.ilike(pattern))
            count_statement = count_statement.where(Project.name.ilike(pattern))

        items = list(
            self.session.scalars(
                statement.order_by(Project.updated_at.desc()).offset(offset).limit(limit)
            )
        )
        total = self.session.scalar(count_statement) or 0
        return items, total

    def delete(self, project: Project) -> None:
        self.session.delete(project)

