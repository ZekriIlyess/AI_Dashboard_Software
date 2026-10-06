from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, SecretStr, Field, ConfigDict

from app.models.user import User
from app.core.security import get_password_hash, verify_password, create_access_token, get_current_user
from app.database import get_db

# ---------------------------------------------------------------------------
# Pydantic v2 schemas
# ---------------------------------------------------------------------------

class UserBase(BaseModel):
    name: str | None = None

class UserCreate(UserBase):
    email: EmailStr = Field(..., description="User e-mail address")
    password: SecretStr = Field(..., description="Plain text password")

class UserLogin(UserBase):
    email: EmailStr
    password: SecretStr

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    email: str
    name: str | None = None

# ---------------------------------------------------------------------------
# Router creation
# ---------------------------------------------------------------------------

router = APIRouter()

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new user if the e-mail is not already taken."""
    stmt_check = select(User).where(User.email == user_in.email)
    result = await db.execute(stmt_check)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed_password = get_password_hash(user_in.password.get_secret_value())
    new_user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        name=user_in.name,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # We return the SQLAlchemy object, and Pydantic will serialize it because of from_attributes=True
    # Need to convert UUID to string for the UserOut schema
    new_user.id = str(new_user.id)
    return new_user


@router.post("/login", response_model=Token)
async def login_for_access_token(
    user_in: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate a user and return a bearer token if credentials are valid."""
    stmt = select(User).where(User.email == user_in.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect e-mail or password",
        )
        
    if not verify_password(user_in.password.get_secret_value(), user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect e-mail or password",
        )

    access_token = create_access_token({"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserOut)
async def read_current_user(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user."""
    current_user.id = str(current_user.id)
    return current_user
