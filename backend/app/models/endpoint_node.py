from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.project import utc_now


class EndpointNode(Base):
    __tablename__ = "endpoint_nodes"
    __table_args__ = (UniqueConstraint("endpoint_id", name="uq_endpoint_node_endpoint"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    endpoint_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("api_endpoints.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("code_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
