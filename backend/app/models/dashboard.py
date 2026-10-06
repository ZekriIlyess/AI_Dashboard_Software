"""Dashboard and DashboardWidget ORM models.

Represents saved dashboards with their grid-layout widgets.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Dashboard(Base):
    """A user-owned dashboard containing multiple widgets."""

    __tablename__ = "dashboards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    theme: Mapped[str] = mapped_column(String(50), default="light")
    global_filters: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=None,
        doc="Serialised list of FilterConfig applied across all widgets",
    )
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="dashboards")  # noqa: F821
    widgets: Mapped[list["DashboardWidget"]] = relationship(
        back_populates="dashboard", cascade="all, delete-orphan",
        lazy="selectin", order_by="DashboardWidget.position_y, DashboardWidget.position_x",
    )

    def __repr__(self) -> str:
        return f"<Dashboard '{self.title}' widgets={len(self.widgets)}>"


class DashboardWidget(Base):
    """A single widget placed on a dashboard."""

    __tablename__ = "dashboard_widgets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dashboard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dashboards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), default="")
    widget_type: Mapped[str] = mapped_column(
        String(50), default="chart",
        doc="'chart' | 'text' | 'kpi' | 'table'",
    )
    chart_config: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        doc="Serialised ChartConfig",
    )
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_source: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Query ID or inline SQL"
    )
    # Grid position (12-column layout)
    position_x: Mapped[int] = mapped_column(Integer, default=0)
    position_y: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[int] = mapped_column(Integer, default=6)
    height: Mapped[int] = mapped_column(Integer, default=4)
    refresh_interval_seconds: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    dashboard: Mapped["Dashboard"] = relationship(back_populates="widgets")

    def __repr__(self) -> str:
        return f"<DashboardWidget '{self.title}' @ ({self.position_x},{self.position_y})>"
