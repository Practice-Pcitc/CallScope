from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.scan import ScanTaskData, ScanTaskResponse
from app.services.scan_service import ScanService, execute_scan_task

router = APIRouter(prefix="/projects")


@router.post(
    "/{project_id}/scan",
    response_model=ScanTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="启动项目文件扫描",
)
def start_scan(
    project_id: str,
    background_tasks: BackgroundTasks,
    session: Annotated[Session, Depends(get_db)],
) -> ScanTaskResponse:
    task = ScanService(session).start(project_id)
    background_tasks.add_task(execute_scan_task, task.id)
    return ScanTaskResponse(data=ScanTaskData.from_entity(task))


@router.get(
    "/{project_id}/scan-status",
    response_model=ScanTaskResponse,
    summary="查询最新扫描状态",
)
def get_scan_status(
    project_id: str,
    session: Annotated[Session, Depends(get_db)],
) -> ScanTaskResponse:
    task = ScanService(session).latest(project_id)
    return ScanTaskResponse(data=ScanTaskData.from_entity(task))

