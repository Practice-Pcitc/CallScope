from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import ProjectScanStatus

if TYPE_CHECKING:
    from app.models.scan_task import ScanTask


def utc_now() -> datetime:
    return datetime.now(UTC)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    root_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    language: Mapped[str] = mapped_column(String(32), nullable=False, default="python")
    framework: Mapped[str] = mapped_column(String(32), nullable=False, default="fastapi")
    scan_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default=ProjectScanStatus.NOT_SCANNED.value
    )
    active_revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    total_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_endpoints: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    scan_tasks: Mapped[list[ScanTask]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
