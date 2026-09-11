from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import ScanStage, ScanTaskStatus
from app.models.project import utc_now

if TYPE_CHECKING:
    from app.models.project import Project


class ScanTask(Base):
    __tablename__ = "scan_tasks"
    __table_args__ = (
        Index("ix_scan_tasks_project_created", "project_id", "created_at"),
        Index("ix_scan_tasks_project_status", "project_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    revision_id: Mapped[str] = mapped_column(
        String(36), nullable=False, default=lambda: str(uuid4())
    )
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default=ScanTaskStatus.PENDING.value
    )
    stage: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ScanStage.DISCOVERY.value
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_file: Mapped[str | None] = mapped_column(Text, nullable=True)
    discovered_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_summary: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    project: Mapped[Project] = relationship(back_populates="scan_tasks")

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
