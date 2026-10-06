from __future__ import annotations

import logging
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.dashboard import Dashboard, DashboardWidget

logger = logging.getLogger(__name__)

class DashboardService:
    """Service handling dashboard retrieving logic."""

    @staticmethod
    async def get_user_dashboards(db: AsyncSession, user_id: uuid.UUID) -> List[Dashboard]:
        """Retrieve all dashboards owned by a user ordered by creation date."""
        stmt = (
            select(Dashboard)
            .where(Dashboard.owner_id == user_id)
            .order_by(Dashboard.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_dashboard_with_widgets(
        db: AsyncSession,
        dashboard_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[Dashboard]:
        """Fetch dashboard and verify owner has access."""
        stmt = select(Dashboard).where(
            Dashboard.id == dashboard_id,
            Dashboard.owner_id == user_id
        )
        result = await db.execute(stmt)
        dashboard = result.scalar_one_or_none()
        
        if dashboard:
            # Explicitly load widgets
            widget_stmt = select(DashboardWidget).where(
                DashboardWidget.dashboard_id == dashboard_id
            )
            widget_res = await db.execute(widget_stmt)
            widgets = widget_res.scalars().all()
            dashboard.widgets = list(widgets)
            
        return dashboard
