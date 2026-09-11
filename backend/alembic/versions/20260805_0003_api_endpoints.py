"""创建 FastAPI 接口表。

Revision ID: 20260805_0003
Revises: 20260805_0002
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260805_0003"
down_revision: str | None = "20260805_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "api_endpoints",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("scan_revision_id", sa.String(length=36), nullable=False),
        sa.Column("http_method", sa.String(length=12), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("function_name", sa.String(length=255), nullable=False),
        sa.Column("qualified_name", sa.Text(), nullable=False),
        sa.Column("module_name", sa.Text(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("response_type", sa.Text(), nullable=True),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "scan_revision_id",
            "http_method",
            "path",
            "qualified_name",
            name="uq_api_endpoint_identity",
        ),
    )
    op.create_index(
        "ix_api_endpoints_project_revision",
        "api_endpoints",
        ["project_id", "scan_revision_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_api_endpoints_project_revision", table_name="api_endpoints")
    op.drop_table("api_endpoints")
