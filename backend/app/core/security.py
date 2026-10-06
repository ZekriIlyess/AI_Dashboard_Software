from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models.user import User

import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# ---------------------------------------------------------------------------
# JWT handling
# ---------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + (expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

# ---------------------------------------------------------------------------
# Fernet encryption (AES-256) for storing credentials
# ---------------------------------------------------------------------------
# The Fernet key must be a URL-safe base64-encoded 32-byte key.
fernet = Fernet(settings.ENCRYPTION_KEY.encode() if isinstance(settings.ENCRYPTION_KEY, str) else settings.ENCRYPTION_KEY)

def encrypt_password(plain_text: str) -> str:
    """Encrypt a plain-text credential using AES-256."""
    return fernet.encrypt(plain_text.encode()).decode()

def decrypt_password(cipher_text: str) -> str:
    """Decrypt a previously encrypted credential."""
    try:
        return fernet.decrypt(cipher_text.encode()).decode()
    except Exception as exc:
        raise ValueError("Failed to decrypt credentials") from exc

# ---------------------------------------------------------------------------
# Dependency that returns the authenticated User instance.
# ---------------------------------------------------------------------------
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    try:
        stmt = select(User).where(User.id == uuid.UUID(user_id_str))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
    except Exception:
        raise credentials_exception

    if not user:
        raise credentials_exception

    return user
