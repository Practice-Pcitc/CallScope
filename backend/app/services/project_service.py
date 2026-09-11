from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import ScanTaskStatus
from app.core.exceptions import AppException
from app.models.project import Project
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.scan_repository import ScanRepository
from app.schemas.project import ProjectCreate


class ProjectService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.projects = ProjectRepository(session)
        self.scans = ScanRepository(session)

    def create(self, payload: ProjectCreate) -> Project:
        root_path = self.validate_root_path(payload.root_path)
        if self.projects.get_by_root_path(root_path):
            raise AppException(
                code="PROJECT_PATH_EXISTS",
                message="该项目路径已经导入",
                status_code=409,
                details={"rootPath": root_path},
            )

        project = Project(name=payload.name, root_path=root_path)
        try:
            self.projects.add(project)
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise AppException(
                code="PROJECT_PATH_EXISTS",
                message="该项目路径已经导入",
                status_code=409,
            ) from exc
        self.session.refresh(project)
        return project

    def get(self, project_id: str) -> Project:
        project = self.projects.get(project_id)
        if not project:
            raise AppException(
                code="PROJECT_NOT_FOUND",
                message="项目不存在",
                status_code=404,
            )
        return project

    def list(self, *, search: str | None, page: int, page_size: int) -> tuple[list[Project], int]:
        return self.projects.list(
            search=search,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

    def delete(self, project_id: str) -> None:
        project = self.get(project_id)
        running = self.scans.get_running(project_id)
        if running and running.status in {
            ScanTaskStatus.PENDING.value,
            ScanTaskStatus.RUNNING.value,
        }:
            raise AppException(
                code="SCAN_IN_PROGRESS",
                message="扫描进行中，暂时不能删除项目",
                status_code=409,
            )
        if AIAnalysisRepository(self.session).has_running(project_id):
            raise AppException(
                code="AI_ANALYSIS_IN_PROGRESS",
                message="AI 分析进行中，暂时不能删除项目",
                status_code=409,
            )
        self.projects.delete(project)
        self.session.commit()

    @staticmethod
    def validate_root_path(raw_path: str) -> str:
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            raise AppException(
                code="INVALID_PROJECT_PATH",
                message="项目路径必须是绝对路径",
                details={"field": "rootPath"},
            )

        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise AppException(
                code="INVALID_PROJECT_PATH",
                message="项目路径不存在或无法访问",
                details={"field": "rootPath"},
            ) from exc

        if not resolved.is_dir():
            raise AppException(
                code="INVALID_PROJECT_PATH",
                message="项目路径必须指向目录",
                details={"field": "rootPath"},
            )
        if not os.access(resolved, os.R_OK | os.X_OK):
            raise AppException(
                code="PROJECT_PATH_UNREADABLE",
                message="项目目录不可读取",
                details={"field": "rootPath"},
            )
        return str(resolved)
