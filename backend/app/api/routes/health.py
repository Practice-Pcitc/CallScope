from fastapi import APIRouter

from app.core.config import settings
from app.core.database import check_database
from app.schemas.health import HealthData, HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="服务健康检查",
)
def health_check() -> HealthResponse:
    """检查应用和数据库是否可以正常响应。"""
    check_database()
    return HealthResponse(
        data=HealthData(
            status="ok",
            service=settings.app_name,
            version=settings.app_version,
            database="ok",
        )
    )
