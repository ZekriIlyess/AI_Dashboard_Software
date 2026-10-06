from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.connection import DatabaseConnection
from app.core.security import get_current_user, encrypt_password
from app.database import get_db

# ---------------------------------------------------------------------------
# Pydantic schemas (v2)
# ---------------------------------------------------------------------------
class ConnectionBase(BaseModel):
    db_type: str = Field(..., description="Database type (e.g., 'postgres', 'mysql')")
    host: str
    port: int
    database: str
    username: str

class ConnectionCreate(ConnectionBase):
    password: SecretStr = Field(..., description="Plain-text DB user password")

class ConnectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    db_type: str
    host: str
    port: int
    database: str
    username: str

# ---------------------------------------------------------------------------
# APIRouter
# ---------------------------------------------------------------------------
router = APIRouter()

# ---------------------------------------------------------------------------
# POST /test
# ---------------------------------------------------------------------------
@router.post("/test")
async def test_connection(
    payload: ConnectionCreate,
    db: AsyncSession = Depends(get_db),
):
    from nexus_connectors.postgresql import PostgreSQLConnector
    from nexus_connectors.mysql import MySQLConnector
    from nexus_connectors.sqlite import SQLiteConnector
    from nexus_connectors.snowflake import SnowflakeConnector
    from nexus_connectors.bigquery import BigQueryConnector
    
    db_type = payload.db_type.lower()
    connector = None
    
    if db_type in ["postgres", "postgresql"]:
        connector = PostgreSQLConnector(
            host=payload.host,
            port=payload.port,
            database=payload.database,
            user=payload.username,
            password=payload.password.get_secret_value(),
        )
    elif db_type == "mysql":
        connector = MySQLConnector(
            host=payload.host,
            port=payload.port,
            database=payload.database,
            user=payload.username,
            password=payload.password.get_secret_value(),
        )
    elif db_type == "sqlite":
        connector = SQLiteConnector(database_path=payload.host)
    elif db_type == "snowflake":
        connector = SnowflakeConnector(
            account=payload.host,
            user=payload.username,
            password=payload.password.get_secret_value(),
            database=payload.database,
        )
    elif db_type == "bigquery":
        # For BigQuery: host is the JSON key path, database is project_id
        connector = BigQueryConnector(
            host=payload.host,
            project_id=payload.database,
        )

    if not connector:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported db_type '{payload.db_type}'. Supported: PostgreSQL, MySQL, SQLite, Snowflake, BigQuery.",
        )

    try:
        await connector.test_connection()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection test failed: {str(exc)}",
        )

    return {"status": "success"}

# ---------------------------------------------------------------------------
# POST /
# ---------------------------------------------------------------------------
@router.post("/", response_model=ConnectionOut)
async def create_connection(
    payload: ConnectionCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    encrypted_pw = encrypt_password(payload.password.get_secret_value())

    new_conn = DatabaseConnection(
        user_id=current_user.id,
        db_type=payload.db_type,
        host=payload.host,
        port=payload.port,
        database=payload.database,
        username=payload.username,
        encrypted_password=encrypted_pw,
    )

    db.add(new_conn)
    await db.commit()
    await db.refresh(new_conn)
    
    new_conn.id = str(new_conn.id)
    return new_conn

# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------
@router.get("/", response_model=list[ConnectionOut])
async def list_connections(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(DatabaseConnection).where(
        DatabaseConnection.user_id == current_user.id
    )
    result = await db.execute(stmt)
    connections = result.scalars().all()
    
    # Cast UUID to str for the pydantic schema
    for conn in connections:
        conn.id = str(conn.id)

    return connections

# ---------------------------------------------------------------------------
# DELETE /{connection_id}
# ---------------------------------------------------------------------------
@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(DatabaseConnection).where(
        DatabaseConnection.id == connection_id,
        DatabaseConnection.user_id == current_user.id
    )
    result = await db.execute(stmt)
    conn = result.scalar_one_or_none()

    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database connection not found",
        )

    await db.delete(conn)
    await db.commit()
    return None
