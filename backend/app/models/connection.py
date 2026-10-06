from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime as SQLDateTime, Integer, String, text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class DatabaseConnection(Base):
    __tablename__ = "database_connections"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    db_type: Mapped[str] = mapped_column(String(32), nullable=False)

    host: Mapped[str] = mapped_column(String(256), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)

    database: Mapped[Optional[str]] = mapped_column(String(100))
    username: Mapped[Optional[str]] = mapped_column(String(100))

    encrypted_password: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        default=func.now(),
    )

    # -----------------------------------------------------------------
    # Back-reference to the owning User (many-to-one)
    # -----------------------------------------------------------------
    user: Mapped["User"] = relationship(back_populates="connections")

    queries: Mapped[list["QueryHistory"]] = relationship(
        back_populates="connection",
        cascade="all, delete-orphan",
    )
