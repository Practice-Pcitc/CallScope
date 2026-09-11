"""Add audit timestamps without discarding existing scans."""

import sqlalchemy as sa

from alembic import op

revision = "20260909_0006"
down_revision = "20260807_0005"
branch_labels = None
depends_on = None
TABLES = ("api_endpoints", "code_nodes", "code_relations", "scan_tasks", "endpoint_nodes")


def upgrade() -> None:
    for table in TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.func.current_timestamp(),
                )
            )
            if table == "endpoint_nodes":
                batch.add_column(
                    sa.Column(
                        "created_at",
                        sa.DateTime(timezone=True),
                        nullable=False,
                        server_default=sa.func.current_timestamp(),
                    )
                )


def downgrade() -> None:
    for table in reversed(TABLES):
        with op.batch_alter_table(table) as batch:
            if table == "endpoint_nodes":
                batch.drop_column("created_at")
            batch.drop_column("updated_at")
