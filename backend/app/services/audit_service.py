from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

class AuditService:
    """Service to log immutable system and user audit events."""

    @staticmethod
    async def log(
        db: AsyncSession,
        user_id: Optional[uuid.UUID],
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Create and commit a new audit log entry."""
        try:
            log_entry = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.add(log_entry)
            await db.commit()
            await db.refresh(log_entry)
            return log_entry
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            # Do not raise exception so calling transactions don't fail because of logging
            await db.rollback()
            return None
