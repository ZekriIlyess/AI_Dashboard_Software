from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_password, get_current_user
from app.database import get_db
from app.models.connection import DatabaseConnection
from app.models.dashboard import Dashboard, DashboardWidget
from app.services.export_service import ExportService

# Import connectors to run widget queries on the fly
from nexus_connectors.postgresql import PostgreSQLConnector
from nexus_connectors.mysql import MySQLConnector
from nexus_connectors.sqlite import SQLiteConnector
from nexus_connectors.snowflake import SnowflakeConnector
from nexus_connectors.bigquery import BigQueryConnector

logger = logging.getLogger(__name__)

router = APIRouter(tags=["exports"])

# ---------- Schemas ----------

class CSVExportRequest(BaseModel):
    filename: Optional[str] = "export.csv"
    data: List[Dict[str, Any]]

class JSONExportRequest(BaseModel):
    filename: Optional[str] = "export.json"
    data: List[Dict[str, Any]]


# ---------- Helper to build database connector ----------

def _build_connector(conn: DatabaseConnection, decrypted_password: str | None):
    db_type = conn.db_type
    if db_type in ("postgresql", "postgres"):
        return PostgreSQLConnector(
            host=conn.host, port=conn.port, database=conn.database,
            user=conn.username, password=decrypted_password,
        )
    elif db_type == "mysql":
        return MySQLConnector(
            host=conn.host, port=conn.port, database=conn.database,
            user=conn.username, password=decrypted_password,
        )
    elif db_type == "sqlite":
        return SQLiteConnector(database_path=conn.host)
    elif db_type == "snowflake":
        return SnowflakeConnector(
            account=conn.host, user=conn.username,
            password=decrypted_password, database=conn.database,
        )
    elif db_type == "bigquery":
        return BigQueryConnector(host=conn.host, project_id=conn.database)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


# ---------- Endpoints ----------

@router.post("/csv")
async def export_to_csv(
    request: CSVExportRequest,
    user = Depends(get_current_user),
):
    """Convert raw payload data to downloadable CSV file."""
    try:
        csv_str = ExportService.export_csv(request.data)
        import io
        csv_io = io.StringIO(csv_str)
        filename = request.filename or "export.csv"
        if not filename.endswith(".csv"):
            filename += ".csv"
        
        return StreamingResponse(
            iter([csv_io.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CSV export failed: {exc}"
        )


@router.post("/json")
async def export_to_json(
    request: JSONExportRequest,
    user = Depends(get_current_user),
):
    """Convert raw payload data to downloadable JSON file."""
    try:
        json_str = ExportService.export_json(request.data)
        import io
        json_io = io.StringIO(json_str)
        filename = request.filename or "export.json"
        if not filename.endswith(".json"):
            filename += ".json"

        return StreamingResponse(
            iter([json_io.getvalue()]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"JSON export failed: {exc}"
        )


@router.get("/pdf/dashboard/{dashboard_id}")
async def export_dashboard_pdf(
    dashboard_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """Fetch dashboard and its widgets, run active queries, compile ReportLab PDF."""
    # 1. Fetch dashboard
    stmt = select(Dashboard).where(
        Dashboard.id == dashboard_id,
        Dashboard.owner_id == user.id
    )
    result = await db.execute(stmt)
    dashboard = result.scalar_one_or_none()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    # 2. Fetch widgets
    widget_stmt = select(DashboardWidget).where(
        DashboardWidget.dashboard_id == dashboard_id
    )
    widget_result = await db.execute(widget_stmt)
    widgets = widget_result.scalars().all()

    # 3. Fetch data for each widget on the fly
    compiled_widgets_data = []
    
    for w in widgets:
        widget_data = []
        if w.data_source and w.connection_id:
            try:
                # Resolve connection
                conn_stmt = select(DatabaseConnection).where(
                    DatabaseConnection.id == uuid.UUID(w.connection_id),
                    DatabaseConnection.user_id == user.id
                )
                conn_res = await db.execute(conn_stmt)
                conn = conn_res.scalar_one_or_none()
                
                if conn:
                    decrypted_pw = decrypt_password(conn.encrypted_password) if conn.encrypted_password else None
                    connector = _build_connector(conn, decrypted_pw)
                    widget_data = await connector.execute_query(w.data_source)
            except Exception as e:
                logger.error(f"Failed to execute query for widget {w.id}: {e}")
                # We'll continue and output empty data instead of crashing the entire export
                widget_data = []

        compiled_widgets_data.append({
            "title": w.title,
            "type": w.widget_type,
            "query": w.data_source,
            "data": widget_data or []
        })

    # 4. Generate PDF
    try:
        creator_name = user.email.split("@")[0] if user.email else "Nexus User"
        pdf_bytes = ExportService.generate_dashboard_pdf(
            dashboard_name=dashboard.title,
            widgets=compiled_widgets_data,
            creator_name=creator_name
        )

        import io
        pdf_io = io.BytesIO(pdf_bytes)

        safe_title = "".join(c for c in dashboard.title if c.isalnum() or c in (" ", "_", "-")).rstrip()
        filename = f"{safe_title.replace(' ', '_')}_Report.pdf"

        return StreamingResponse(
            pdf_io,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as exc:
        logger.exception("PDF generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF generation failed: {exc}"
        )
