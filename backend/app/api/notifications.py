from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.database import get_db
from app.models.notification import Notification

logger = logging.getLogger(__name__)

router = APIRouter(tags=["notifications"])

# ---------- Schemas ----------

class NotificationOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    type: str
    title: str
    message: str
    read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Endpoints ----------

@router.get("/", response_model=List[NotificationOut])
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """Retrieve all notifications for the authenticated user."""
    stmt = (
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.put("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """Mark a specific notification as read."""
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user.id
    )
    result = await db.execute(stmt)
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.read = True
    await db.commit()
    await db.refresh(notification)
    return notification


@router.put("/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """Mark all notifications as read for the user."""
    stmt = (
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read == False)
        .values(read=True)
    )
    await db.execute(stmt)
    await db.commit()
    return {"status": "success", "message": "All notifications marked as read"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """Delete a specific notification."""
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user.id
    )
    result = await db.execute(stmt)
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    await db.delete(notification)
    await db.commit()
    return {"status": "success", "message": "Notification deleted"}
