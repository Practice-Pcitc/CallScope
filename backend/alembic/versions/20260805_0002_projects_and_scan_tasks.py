"""创建项目与扫描任务表。

Revision ID: 20260805_0002
Revises: 20260805_0001
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260805_0002"
down_revision: str | None = "20260805_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("root_path", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=32), nullable=False),
        sa.Column("framework", sa.String(length=32), nullable=False),
        sa.Column("scan_status", sa.String(length=24), nullable=False),
        sa.Column("active_revision_id", sa.String(length=36), nullable=True),
        sa.Column("total_files", sa.Integer(), nullable=False),
        sa.Column("total_endpoints", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("root_path"),
    )
    op.create_index("ix_projects_name", "projects", ["name"], unique=False)

    op.create_table(
        "scan_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("revision_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("current_file", sa.Text(), nullable=True),
        sa.Column("discovered_files", sa.Integer(), nullable=False),
        sa.Column("processed_files", sa.Integer(), nullable=False),
        sa.Column("skipped_files", sa.Integer(), nullable=False),
        sa.Column("failed_files", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_summary", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scan_tasks_project_created",
        "scan_tasks",
        ["project_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_scan_tasks_project_status",
        "scan_tasks",
        ["project_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_scan_tasks_project_status", table_name="scan_tasks")
    op.drop_index("ix_scan_tasks_project_created", table_name="scan_tasks")
    op.drop_table("scan_tasks")
    op.drop_index("ix_projects_name", table_name="projects")
    op.drop_table("projects")
