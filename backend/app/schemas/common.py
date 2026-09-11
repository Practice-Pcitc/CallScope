from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ApiModel(BaseModel):
    """统一使用 camelCase 输出，同时允许 Python 内部使用 snake_case。"""

    model_config = ConfigDict(
        alias_generator=lambda value: "".join(
            word.capitalize() if index else word for index, word in enumerate(value.split("_"))
        ),
        populate_by_name=True,
    )

    @field_validator("*", mode="after")
    @classmethod
    def normalize_datetime(cls, value: Any) -> Any:
        # SQLite returns naive values even for DateTime(timezone=True).
        if isinstance(value, datetime):
            return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        return value


class ErrorBody(ApiModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str = Field(serialization_alias="requestId")


class ErrorEnvelope(ApiModel):
    error: ErrorBody


class PaginationMeta(ApiModel):
    page: int
    page_size: int
    total: int
