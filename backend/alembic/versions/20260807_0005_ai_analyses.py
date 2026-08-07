"""创建 AI 链路分析缓存表。

Revision ID: 20260807_0005
Revises: 20260805_0004
Create Date: 2026-08-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260807_0005"
down_revision: str | None = "20260805_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_analyses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("scan_revision_id", sa.String(length=36), nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("scope_key", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("graph_version", sa.String(length=64), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("context_hash", sa.String(length=64), nullable=False),
        sa.Column("cache_key", sa.String(length=64), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("token_usage", sa.JSON(), nullable=False),
        sa.Column("invalid_reference_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stale_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_analyses_cache_key",
        "ai_analyses",
        ["cache_key"],
        unique=True,
    )
    op.create_index(
        "ix_ai_analyses_project_revision",
        "ai_analyses",
        ["project_id", "scan_revision_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ai_analyses_project_revision", table_name="ai_analyses")
    op.drop_index("ix_ai_analyses_cache_key", table_name="ai_analyses")
    op.drop_table("ai_analyses")
