from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.analyzers.call_graph_analyzer import CallGraphAnalyzer
from app.analyzers.fastapi_analyzer import FastAPIProjectAnalyzer
from app.analyzers.file_scanner import FileScanner, ScanLimitError
from app.analyzers.java_spring_analyzer import JavaSpringProjectAnalyzer
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.enums import ProjectScanStatus, ScanStage, ScanTaskStatus
from app.core.exceptions import AppException
from app.core.logging import logger
from app.models.api_endpoint import ApiEndpoint
from app.models.code_node import CodeNode
from app.models.code_relation import CodeRelation
from app.models.endpoint_node import EndpointNode
from app.models.scan_task import ScanTask
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.endpoint_repository import EndpointRepository
from app.repositories.graph_repository import GraphRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.scan_repository import ScanRepository


def utc_now() -> datetime:
    return datetime.now(UTC)


class ScanService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.projects = ProjectRepository(session)
        self.scans = ScanRepository(session)

    def start(self, project_id: str) -> ScanTask:
        project = self.projects.get(project_id)
        if not project:
            raise AppException(
                code="PROJECT_NOT_FOUND",
                message="项目不存在",
                status_code=404,
            )
        if self.scans.get_running(project_id):
            raise AppException(
                code="SCAN_ALREADY_RUNNING",
                message="该项目已有扫描任务正在运行",
                status_code=409,
            )

        task = ScanTask(project_id=project.id)
        self.scans.add(task)
        project.scan_status = ProjectScanStatus.SCANNING.value
        self.session.commit()
        self.session.refresh(task)
        return task

    def latest(self, project_id: str) -> ScanTask:
        if not self.projects.get(project_id):
            raise AppException(
                code="PROJECT_NOT_FOUND",
                message="项目不存在",
                status_code=404,
            )
        task = self.scans.get_latest(project_id)
        if not task:
            raise AppException(
                code="SCAN_NOT_FOUND",
                message="该项目还没有扫描记录",
                status_code=404,
            )
        return task


def execute_scan_task(task_id: str) -> None:
    """后台执行安全文件发现；使用独立 Session，避免复用请求会话。"""
    with SessionLocal() as session:
        scans = ScanRepository(session)
        projects = ProjectRepository(session)
        task = scans.get(task_id)
        if not task:
            return
        project = projects.get(task.project_id)
        if not project:
            return

        task.status = ScanTaskStatus.RUNNING.value
        task.stage = ScanStage.DISCOVERY.value
        task.progress = 2
        task.started_at = utc_now()
        session.commit()

        scanner = FileScanner(
            ignored_directories=set(settings.ignored_directories),
            max_files=settings.max_scan_files,
            max_file_size_bytes=settings.max_file_size_bytes,
            max_directory_entries=settings.max_directory_entries,
            error_limit=settings.scan_error_limit,
        )

        def update_discovery_progress(current_file: str, visited_entries: int) -> None:
            task.current_file = current_file
            task.progress = min(
                60,
                5 + int(visited_entries / max(settings.max_directory_entries, 1) * 55),
            )
            session.commit()

        try:
            result = scanner.discover(
                Path(project.root_path),
                on_progress=update_discovery_progress,
            )
            python_files = [path for path in result.files if Path(path).suffix.casefold() == ".py"]
            java_files = [path for path in result.files if Path(path).suffix.casefold() == ".java"]
            if java_files and len(java_files) >= len(python_files):
                source_files = java_files
                project.language = "java"
                project.framework = "spring"
            else:
                source_files = python_files
                project.language = "python"
                project.framework = "fastapi"

            task.stage = ScanStage.VALIDATE.value
            task.progress = 58
            task.discovered_files = len(source_files)
            task.skipped_files = result.skipped_files
            task.failed_files = result.failed_files
            task.error_summary = [error.as_dict() for error in result.errors]
            if source_files:
                task.current_file = source_files[-1]
            session.commit()

            task.stage = ScanStage.PARSE.value
            task.progress = 62
            session.commit()

            def update_parse_progress(
                current_file: str,
                current_index: int,
                total_files: int,
            ) -> None:
                task.current_file = current_file
                task.processed_files = current_index
                task.progress = 62 + int(current_index / max(total_files, 1) * 26)
                if current_index % 20 == 0 or current_index == total_files:
                    session.commit()

            if project.language == "java":
                java_analysis = JavaSpringProjectAnalyzer().analyze(
                    root=Path(project.root_path),
                    files=source_files,
                    on_progress=update_parse_progress,
                )
                analysis = java_analysis.endpoints
                graph_analysis = java_analysis.graph
            else:
                analysis = FastAPIProjectAnalyzer().analyze(
                    root=Path(project.root_path),
                    files=source_files,
                    on_progress=update_parse_progress,
                )
                graph_analysis = CallGraphAnalyzer().analyze(
                    root=Path(project.root_path),
                    files=source_files,
                    endpoints=analysis.endpoints,
                )
            task.stage = ScanStage.RESOLVE.value
            task.progress = 90
            task.failed_files += len(analysis.issues)
            task.error_summary = [
                *task.error_summary,
                *[issue.as_dict() for issue in analysis.issues],
            ][: settings.scan_error_limit]
            session.commit()

            task.failed_files += len(graph_analysis.issues)
            task.error_summary = [
                *task.error_summary,
                *graph_analysis.issues,
            ][: settings.scan_error_limit]
            task.progress = 94
            session.commit()

            task.stage = ScanStage.PERSIST.value
            task.progress = 95
            task.processed_files = len(source_files)
            endpoint_repository = EndpointRepository(session)
            endpoint_entities = [
                ApiEndpoint(
                    project_id=project.id,
                    scan_revision_id=task.revision_id,
                    **endpoint,
                )
                for endpoint in analysis.endpoints
            ]
            endpoint_repository.add_many(endpoint_entities)

            graph_repository = GraphRepository(session)
            node_entities = [
                CodeNode(
                    project_id=project.id,
                    scan_revision_id=task.revision_id,
                    **node_data,
                )
                for node_data in graph_analysis.nodes.values()
            ]
            graph_repository.add_nodes(node_entities)
            node_id_by_key = {node.stable_key: node.id for node in node_entities}
            relation_entities = [
                CodeRelation(
                    project_id=project.id,
                    scan_revision_id=task.revision_id,
                    source_node_id=node_id_by_key[relation["source_key"]],
                    target_node_id=node_id_by_key[relation["target_key"]],
                    **{
                        key: value
                        for key, value in relation.items()
                        if key not in {"source_key", "target_key"}
                    },
                )
                for relation in graph_analysis.relations.values()
                if relation["source_key"] in node_id_by_key
                and relation["target_key"] in node_id_by_key
            ]
            graph_repository.add_relations(relation_entities)
            endpoint_by_identity = {
                (
                    endpoint.http_method,
                    endpoint.path,
                    endpoint.qualified_name,
                ): endpoint
                for endpoint in endpoint_entities
            }
            graph_repository.add_endpoint_nodes(
                [
                    EndpointNode(
                        endpoint_id=endpoint_by_identity[identity].id,
                        node_id=node_id_by_key[api_key],
                    )
                    for identity, api_key in (graph_analysis.endpoint_api_keys.items())
                    if identity in endpoint_by_identity and api_key in node_id_by_key
                ]
            )
            project.total_files = len(source_files)
            project.total_endpoints = len(analysis.endpoints)
            project.scan_status = ProjectScanStatus.READY.value
            session.commit()

            task.status = ScanTaskStatus.SUCCEEDED.value
            task.stage = ScanStage.COMPLETED.value
            task.progress = 100
            task.current_file = None
            task.finished_at = utc_now()
            project.active_revision_id = task.revision_id
            AIAnalysisRepository(session).mark_project_stale(
                project_id=project.id,
                active_revision_id=task.revision_id,
            )
            session.commit()
        except ScanLimitError as exc:
            _fail_task(
                session,
                task_id=task.id,
                project_id=project.id,
                message=str(exc),
            )
        except Exception as exc:
            logger.error("scan_failed", extra={"run_id": task.id, "error_type": type(exc).__name__})
            _fail_task(
                session,
                task_id=task.id,
                project_id=project.id,
                message="扫描失败，请检查项目可读性并凭扫描编号排查",
            )


def _fail_task(
    session: Session,
    *,
    task_id: str,
    project_id: str,
    message: str,
) -> None:
    session.rollback()
    task = ScanRepository(session).get(task_id)
    project = ProjectRepository(session).get(project_id)
    if not task or not project:
        return
    task.status = ScanTaskStatus.FAILED.value
    task.progress = min(task.progress, 99)
    task.error_message = message
    task.finished_at = utc_now()
    project.scan_status = ProjectScanStatus.FAILED.value
    session.commit()


def recover_interrupted_scans() -> None:
    """服务重启后将遗留 RUNNING/PENDING 任务标记为失败。"""
    with SessionLocal() as session:
        scans = ScanRepository(session)
        count = scans.mark_interrupted_as_failed(message="服务重启，扫描任务已中断")
        if count:
            ProjectRepository(session).mark_scanning_failed()
            session.commit()
