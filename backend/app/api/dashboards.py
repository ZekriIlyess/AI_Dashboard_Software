from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, ConfigDict
import uuid

from app.models.dashboard import Dashboard, DashboardWidget
from app.models.connection import DatabaseConnection
from app.core.security import decrypt_password, get_current_user
from app.database import get_db
from nexus_connectors.postgresql import PostgreSQLConnector
from nexus_connectors.mysql import MySQLConnector
from nexus_connectors.sqlite import SQLiteConnector
from nexus_connectors.snowflake import SnowflakeConnector
from nexus_connectors.bigquery import BigQueryConnector

router = APIRouter(tags=["dashboards"])

# ---------- Schemas ----------

class DashboardCreate(BaseModel):
    title: str
    description: Optional[str] = None
    theme: str = "light"

class DashboardUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    theme: Optional[str] = None

class WidgetCreate(BaseModel):
    title: str
    widget_type: str
    chart_config: Optional[Dict[str, Any]] = None
    text_content: Optional[str] = None
    data_source: Optional[str] = None # The SQL query
    connection_id: str # Required to know where to execute the SQL
    position_x: int = 0
    position_y: int = 0
    width: int = 6
    height: int = 4

class WidgetUpdate(BaseModel):
    title: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    data_source: Optional[str] = None

class WidgetOut(BaseModel):
    id: uuid.UUID
    title: str
    widget_type: str
    chart_config: Optional[Dict[str, Any]] = None
    text_content: Optional[str] = None
    data_source: Optional[str] = None
    position_x: int
    position_y: int
    width: int
    height: int
    
    model_config = ConfigDict(from_attributes=True)

class DashboardOut(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    theme: str
    widgets: List[WidgetOut] = []
    
    model_config = ConfigDict(from_attributes=True)


# ---------- Endpoints ----------

@router.get("/", response_model=List[DashboardOut])
async def list_dashboards(
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    stmt = select(Dashboard).where(Dashboard.owner_id == user.id).order_by(Dashboard.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/", response_model=DashboardOut)
async def create_dashboard(
    data: DashboardCreate,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    dashboard = Dashboard(
        owner_id=user.id,
        title=data.title,
        description=data.description,
        theme=data.theme,
    )
    db.add(dashboard)
    await db.commit()
    await db.refresh(dashboard)
    return dashboard

@router.get("/{dashboard_id}", response_model=DashboardOut)
async def get_dashboard(
    dashboard_id: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    stmt = select(Dashboard).where(Dashboard.id == dashboard_id, Dashboard.owner_id == user.id)
    result = await db.execute(stmt)
    dashboard = result.scalar_one_or_none()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return dashboard

@router.put("/{dashboard_id}", response_model=DashboardOut)
async def update_dashboard(
    dashboard_id: str,
    data: DashboardUpdate,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    try:
        dash_uuid = uuid.UUID(dashboard_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dashboard ID format")

    stmt = select(Dashboard).where(Dashboard.id == dash_uuid, Dashboard.owner_id == user.id)
    result = await db.execute(stmt)
    dashboard = result.scalar_one_or_none()
    
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
        
    if data.title is not None:
        dashboard.title = data.title
    if data.description is not None:
        dashboard.description = data.description
    if data.theme is not None:
        dashboard.theme = data.theme
        
    await db.commit()
    await db.refresh(dashboard)
    return dashboard

@router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard(
    dashboard_id: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    try:
        dash_uuid = uuid.UUID(dashboard_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dashboard ID format")

    stmt = select(Dashboard).where(Dashboard.id == dash_uuid, Dashboard.owner_id == user.id)
    result = await db.execute(stmt)
    dashboard = result.scalar_one_or_none()
    
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
        
    await db.delete(dashboard)
    await db.commit()
    return None

@router.post("/{dashboard_id}/widgets", response_model=WidgetOut)
async def add_widget(
    dashboard_id: str,
    data: WidgetCreate,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    # Verify dashboard exists and belongs to user
    stmt = select(Dashboard).where(Dashboard.id == dashboard_id, Dashboard.owner_id == user.id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Dashboard not found")

    # If it's a chart, we embed the connection_id in the chart_config so we know how to fetch it later
    chart_config = data.chart_config or {}
    chart_config["connection_id"] = data.connection_id

    widget = DashboardWidget(
        dashboard_id=uuid.UUID(dashboard_id),
        title=data.title,
        widget_type=data.widget_type,
        chart_config=chart_config,
        text_content=data.text_content,
        data_source=data.data_source,
        position_x=data.position_x,
        position_y=data.position_y,
        width=data.width,
        height=data.height,
    )
    db.add(widget)
    await db.commit()
    await db.refresh(widget)
    return widget

@router.get("/widgets/{widget_id}/data")
async def get_widget_data(
    widget_id: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """Executes the raw SQL saved in the widget against the target database connection."""
    # 1. Fetch widget and verify ownership through dashboard
    stmt = select(DashboardWidget).join(Dashboard).where(
        DashboardWidget.id == widget_id,
        Dashboard.owner_id == user.id
    )
    result = await db.execute(stmt)
    widget = result.scalar_one_or_none()
    
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
        
    if not widget.data_source:
        return []

    # 2. Extract connection_id
    connection_id = widget.chart_config.get("connection_id") if widget.chart_config else None
    if not connection_id:
        raise HTTPException(status_code=400, detail="Widget is missing connection_id")

    # 3. Fetch connection
    conn_stmt = select(DatabaseConnection).where(
        DatabaseConnection.id == connection_id,
        DatabaseConnection.user_id == user.id
    )
    conn_result = await db.execute(conn_stmt)
    conn = conn_result.scalar_one_or_none()
    
    if not conn:
        raise HTTPException(status_code=404, detail="Database connection not found")

    # 4. Execute SQL
    try:
        decrypted_password = decrypt_password(conn.encrypted_password) if conn.encrypted_password else None
        
        connector = None
        if conn.db_type in ("postgresql", "postgres"):
            connector = PostgreSQLConnector(
                host=conn.host,
                port=conn.port,
                database=conn.database,
                user=conn.username,
                password=decrypted_password,
            )
        elif conn.db_type == "mysql":
            connector = MySQLConnector(
                host=conn.host,
                port=conn.port,
                database=conn.database,
                user=conn.username,
                password=decrypted_password,
            )
        elif conn.db_type == "sqlite":
            connector = SQLiteConnector(database_path=conn.host)
        elif conn.db_type == "snowflake":
            connector = SnowflakeConnector(
                account=conn.host,
                user=conn.username,
                password=decrypted_password,
                database=conn.database,
            )
        elif conn.db_type == "bigquery":
            connector = BigQueryConnector(
                host=conn.host,
                project_id=conn.database,
            )
        else:
            raise Exception(f"Unsupported connection type: {conn.db_type}")
        
        # Security Note: This SQL was generated by the LLM and saved by the user.
        # We assume it is read-only (SELECT).
        results = await connector.execute_query(widget.data_source)
        return results
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.delete("/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_widget(
    widget_id: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    try:
        widget_uuid = uuid.UUID(widget_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid widget ID format")

    stmt = select(DashboardWidget).join(Dashboard).where(
        DashboardWidget.id == widget_uuid,
        Dashboard.owner_id == user.id
    )
    result = await db.execute(stmt)
    widget = result.scalar_one_or_none()
    
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
        
    await db.delete(widget)
    await db.commit()
    return None

@router.put("/widgets/{widget_id}")
async def update_widget(
    widget_id: str,
    payload: WidgetUpdate,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    try:
        widget_uuid = uuid.UUID(widget_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid widget ID format")

    stmt = select(DashboardWidget).join(Dashboard).where(
        DashboardWidget.id == widget_uuid,
        Dashboard.owner_id == user.id
    )
    result = await db.execute(stmt)
    widget = result.scalar_one_or_none()
    
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
        
    if payload.title is not None:
        widget.title = payload.title
    if payload.width is not None:
        widget.width = payload.width
    if payload.height is not None:
        widget.height = payload.height
    if payload.position_x is not None:
        widget.position_x = payload.position_x
    if payload.position_y is not None:
        widget.position_y = payload.position_y
    if payload.data_source is not None:
        widget.data_source = payload.data_source
        
    await db.commit()
    await db.refresh(widget)
    return {
        "id": str(widget.id),
        "title": widget.title,
        "width": widget.width,
        "height": widget.height,
        "position_x": widget.position_x,
        "position_y": widget.position_y,
        "data_source": widget.data_source
    }
