"""创建代码图节点、关系和接口映射表。

Revision ID: 20260805_0004
Revises: 20260805_0003
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260805_0004"
down_revision: str | None = "20260805_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "code_nodes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("scan_revision_id", sa.String(length=36), nullable=False),
        sa.Column("stable_key", sa.Text(), nullable=False),
        sa.Column("node_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("qualified_name", sa.Text(), nullable=False),
        sa.Column("module_name", sa.Text(), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("start_line", sa.Integer(), nullable=True),
        sa.Column("end_line", sa.Integer(), nullable=True),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("source_excerpt", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "scan_revision_id",
            "stable_key",
            name="uq_code_node_stable_key",
        ),
    )
    op.create_index(
        "ix_code_nodes_project_revision_type",
        "code_nodes",
        ["project_id", "scan_revision_id", "node_type"],
        unique=False,
    )

    op.create_table(
        "code_relations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("scan_revision_id", sa.String(length=36), nullable=False),
        sa.Column("stable_key", sa.Text(), nullable=False),
        sa.Column("source_node_id", sa.String(length=36), nullable=False),
        sa.Column("target_node_id", sa.String(length=36), nullable=False),
        sa.Column("relation_type", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.String(length=16), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("line_number", sa.Integer(), nullable=True),
        sa.Column("column_number", sa.Integer(), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_node_id"], ["code_nodes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_node_id"], ["code_nodes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "scan_revision_id",
            "stable_key",
            name="uq_code_relation_stable_key",
        ),
    )
    op.create_index(
        "ix_code_relations_source",
        "code_relations",
        ["project_id", "scan_revision_id", "source_node_id"],
        unique=False,
    )
    op.create_index(
        "ix_code_relations_target",
        "code_relations",
        ["project_id", "scan_revision_id", "target_node_id"],
        unique=False,
    )

    op.create_table(
        "endpoint_nodes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("endpoint_id", sa.String(length=36), nullable=False),
        sa.Column("node_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["endpoint_id"], ["api_endpoints.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["node_id"], ["code_nodes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint_id", name="uq_endpoint_node_endpoint"),
    )


def downgrade() -> None:
    op.drop_table("endpoint_nodes")
    op.drop_index("ix_code_relations_target", table_name="code_relations")
    op.drop_index("ix_code_relations_source", table_name="code_relations")
    op.drop_table("code_relations")
    op.drop_index("ix_code_nodes_project_revision_type", table_name="code_nodes")
    op.drop_table("code_nodes")

