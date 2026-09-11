from datetime import datetime
from typing import Any

from app.schemas.common import ApiModel


class ScanTaskData(ApiModel):
    id: str
    project_id: str
    revision_id: str
    status: str
    stage: str
    progress: int
    current_file: str | None
    discovered_files: int
    processed_files: int
    skipped_files: int
    failed_files: int
    error_message: str | None
    errors: list[dict[str, Any]]
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    @classmethod
    def from_entity(cls, task) -> "ScanTaskData":
        return cls(
            id=task.id,
            project_id=task.project_id,
            revision_id=task.revision_id,
            status=task.status,
            stage=task.stage,
            progress=task.progress,
            current_file=task.current_file,
            discovered_files=task.discovered_files,
            processed_files=task.processed_files,
            skipped_files=task.skipped_files,
            failed_files=task.failed_files,
            error_message=task.error_message,
            errors=task.error_summary,
            started_at=task.started_at,
            finished_at=task.finished_at,
            created_at=task.created_at,
        )


class ScanTaskResponse(ApiModel):
    data: ScanTaskData
