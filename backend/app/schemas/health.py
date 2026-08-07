from typing import Literal

from app.schemas.common import ApiModel


class HealthData(ApiModel):
    status: Literal["ok"]
    service: str
    version: str
    database: Literal["ok"]


class HealthResponse(ApiModel):
    data: HealthData

