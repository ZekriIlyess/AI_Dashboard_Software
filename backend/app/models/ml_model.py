"""MLModel ORM model.

Stores metadata about trained ML models including metrics,
feature importance, and the path to the serialised artifact.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class MLModel(Base):
    """Metadata for a trained ML model."""

    __tablename__ = "ml_models"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    model_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        doc="ModelType enum value",
    )
    task_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        doc="TaskType enum value (regression, classification, …)",
    )
    target_column: Mapped[str] = mapped_column(String(200), nullable=False)
    feature_columns: Mapped[list | None] = mapped_column(
        JSONB, nullable=True,
        doc="List of feature column names used",
    )
    metrics: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        doc="Serialised list of MetricValue",
    )
    feature_importance: Mapped[list | None] = mapped_column(
        JSONB, nullable=True,
        doc="Serialised list of FeatureImportance",
    )
    hyperparameters: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
    )
    training_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    artifact_path: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        doc="File path to the serialised model (joblib/pickle)",
    )
    status: Mapped[str] = mapped_column(
        String(50), default="training", nullable=False,
        doc="'training' | 'completed' | 'failed'",
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<MLModel {self.name} ({self.model_type}) status={self.status}>"
