from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.enums import ScanTaskStatus
from app.models.scan_task import ScanTask


class ScanRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, task: ScanTask) -> ScanTask:
        self.session.add(task)
        self.session.flush()
        return task

    def get(self, task_id: str) -> ScanTask | None:
        return self.session.get(ScanTask, task_id)

    def get_latest(self, project_id: str) -> ScanTask | None:
        statement = (
            select(ScanTask)
            .where(ScanTask.project_id == project_id)
            .order_by(ScanTask.created_at.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    def get_running(self, project_id: str) -> ScanTask | None:
        statement = (
            select(ScanTask)
            .where(
                ScanTask.project_id == project_id,
                ScanTask.status.in_(
                    [ScanTaskStatus.PENDING.value, ScanTaskStatus.RUNNING.value]
                ),
            )
            .order_by(ScanTask.created_at.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    def mark_interrupted_as_failed(self, *, message: str) -> int:
        statement = (
            update(ScanTask)
            .where(
                ScanTask.status.in_(
                    [ScanTaskStatus.PENDING.value, ScanTaskStatus.RUNNING.value]
                )
            )
            .values(
                status=ScanTaskStatus.FAILED.value,
                error_message=message,
            )
        )
        result = self.session.execute(statement)
        return result.rowcount or 0

