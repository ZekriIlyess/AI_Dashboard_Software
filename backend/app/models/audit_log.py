"""AuditLog ORM model.

Immutable, append-only table for tracking user actions across
the platform.  Used for compliance, debugging, and analytics.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AuditLog(Base):
    """Immutable audit log entry."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
        doc="Action verb, e.g. 'query.execute', 'connection.create', 'dashboard.delete'",
    )
    resource_type: Mapped[str] = mapped_column(
        String(100), nullable=False,
        doc="Resource type, e.g. 'connection', 'query', 'dashboard'",
    )
    resource_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        doc="UUID of the affected resource",
    )
    details: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        doc="Arbitrary JSON payload with action-specific details",
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} user={self.user_id} @ {self.created_at}>"
