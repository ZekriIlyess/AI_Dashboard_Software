"""Notification ORM model.

Stores in-app alerts and notifications for users, such as anomaly reports,
auto-ml completion notifications, and system alerts.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

class Notification(Base):
    """Stores in-app notification alerts."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="info"  # "info", "anomaly", "success", "error"
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    message: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    read: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    def __repr__(self) -> str:
        return f"<Notification {self.title} read={self.read} user={self.user_id}>"
