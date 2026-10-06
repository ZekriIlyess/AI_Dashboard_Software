from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime as SQLDateTime, String, text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)

    # optional name field
    name: Mapped[Optional[str]] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(
        SQLDateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        default=func.now(),
    )

    # -----------------------------------------------------------------
    # Relationship to DatabaseConnection (one-to-many)
    # -----------------------------------------------------------------
    connections: Mapped[List["DatabaseConnection"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    query_history: Mapped[List["QueryHistory"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    dashboards: Mapped[List["Dashboard"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )
