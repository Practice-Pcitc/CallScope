from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.common import ApiModel, PaginationMeta


class ProjectCreate(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    root_path: str = Field(min_length=1, max_length=4096)

    @field_validator("name", "root_path", mode="before")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class ProjectData(ApiModel):
    id: str
    name: str
    root_path: str
    language: str
    framework: str
    scan_status: str
    active_revision_id: str | None
    total_files: int
    total_endpoints: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, project) -> "ProjectData":
        return cls.model_validate(project, from_attributes=True)


class ProjectResponse(ApiModel):
    data: ProjectData


class ProjectListData(ApiModel):
    items: list[ProjectData]
    pagination: PaginationMeta


class ProjectListResponse(ApiModel):
    data: ProjectListData
