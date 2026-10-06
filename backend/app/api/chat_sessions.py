from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import uuid
from datetime import datetime

from app.models.chat_session import ChatSession
from app.models.connection import DatabaseConnection
from app.core.security import get_current_user
from app.database import get_db

router = APIRouter(tags=["chat_sessions"])

class ChatSessionResponse(BaseModel):
    id: uuid.UUID
    connection_id: uuid.UUID
    title: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatSessionCreate(BaseModel):
    connection_id: uuid.UUID

@router.post("/", response_model=ChatSessionResponse)
async def create_chat_session(
    request: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    session = ChatSession(
        user_id=user.id,
        connection_id=request.connection_id,
        title="New Chat",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session

@router.get("/", response_model=List[ChatSessionResponse])
async def get_chat_sessions(
    connection_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    stmt = select(ChatSession).where(ChatSession.user_id == user.id)
    if connection_id:
        stmt = stmt.where(ChatSession.connection_id == connection_id)
    stmt = stmt.order_by(ChatSession.created_at.desc())
    
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return sessions

@router.delete("/{session_id}")
async def delete_chat_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    stmt = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.user_id == user.id
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
        
    await db.delete(session)
    await db.commit()
    return {"status": "deleted"}
