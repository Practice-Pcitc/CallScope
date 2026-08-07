"""建立阶段二迁移基线。

Revision ID: 20260805_0001
Revises:
Create Date: 2026-08-05
"""

from collections.abc import Sequence

revision: str = "20260805_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """阶段三加入首批业务表；本迁移只建立可验证的版本基线。"""


def downgrade() -> None:
    """基线迁移没有数据库对象需要删除。"""

