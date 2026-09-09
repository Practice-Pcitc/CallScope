from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.project import Project
from app.repositories.project_repository import ProjectRepository


def test_repository_does_not_commit():
    with SessionLocal() as session:
        ProjectRepository(session).add(
            Project(name="rollback", root_path="/synthetic", language="Python", framework="FastAPI")
        )
        session.rollback()
        assert session.scalar(select(Project)) is None
