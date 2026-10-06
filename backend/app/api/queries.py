from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel

from app.models.connection import DatabaseConnection
from app.models.query_history import QueryHistory
from app.core.security import decrypt_password, get_current_user
from app.database import get_db, AsyncSessionLocal
from app.config import settings
from nexus_connectors.postgresql import PostgreSQLConnector
from nexus_connectors.mysql import MySQLConnector
from nexus_connectors.sqlite import SQLiteConnector
from nexus_connectors.snowflake import SnowflakeConnector
from nexus_connectors.bigquery import BigQueryConnector
from app.agents.llm.local_provider import OllamaProvider
from app.agents.llm.openrouter_provider import OpenRouterProvider
from app.agents.sql_agent import SQLAgent
from app.agents.schema_agent import SchemaAgent
from app.agents.stats_agent import StatsAgent
from app.agents.narrator_agent import NarratorAgent
from app.agents.chart_agent import ChartAgent
from app.agents.brain_agent import BrainAgent
from app.core.query_validator import QueryValidator, QueryValidationError
from app.api.websocket import manager

import uuid
import json
import logging

logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    connection_id: uuid.UUID
    session_id: uuid.UUID
    message: str


class ChatResponse(BaseModel):
    history_id: str
    status: str


# ---------- Router ----------
router = APIRouter(tags=["queries"])


async def process_query_task(
    history_id: uuid.UUID,
    connection_id: uuid.UUID,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    message: str
):
    """
    Background worker that connects to DB, gets schema,
    prompts LLMs, validates SQL, executes, and updates history.
    """
    async with AsyncSessionLocal() as db:
        try:
            # 1. Load connection details
            stmt = select(DatabaseConnection).where(DatabaseConnection.id == connection_id)
            result = await db.execute(stmt)
            conn = result.scalar_one_or_none()
            if not conn:
                raise Exception("Connection deleted before task could run.")

            # Instantiating the appropriate connector
            decrypted_password = decrypt_password(conn.encrypted_password) if conn.encrypted_password else None
            
            connector_class = None
            if conn.db_type in ("postgresql", "postgres"):
                connector_class = PostgreSQLConnector
            elif conn.db_type == "mysql":
                connector_class = MySQLConnector
            elif conn.db_type == "sqlite":
                connector_class = SQLiteConnector
            elif conn.db_type == "snowflake":
                connector_class = SnowflakeConnector
            elif conn.db_type == "bigquery":
                connector_class = BigQueryConnector
            else:
                raise Exception(f"Unsupported connection type: {conn.db_type}")

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

            logger.info(f"[{history_id}] Getting schema...")
            await manager.broadcast_to_session(str(session_id), {"type": "progress", "history_id": str(history_id), "message": "Connecting to database..."})
            schema = await connector.get_schema()
            foreign_keys = await connector.get_foreign_keys()

            # 2. Get recent history to provide context
            # We want the last 3-4 successful queries in this session
            stmt_recent = (
                select(QueryHistory)
                .where(
                    QueryHistory.session_id == session_id,
                    QueryHistory.status == "success"
                )
                .order_by(QueryHistory.created_at.desc())
                .limit(4)
            )
            recent_res = await db.execute(stmt_recent)
            recent_history_records = recent_res.scalars().all()
            
            # Reverse to make it chronological
            recent_history_records.reverse()
            
            history_list = []
            for hr in recent_history_records:
                history_list.append({
                    "user_query": hr.natural_language_query,
                    "sql": hr.generated_sql,
                    "narrative": hr.narrative,
                })

            # 3. LLM pipeline
            logger.info(f"[{history_id}] Calling Schema Agent...")
            await manager.broadcast_to_session(str(session_id), {"type": "progress", "history_id": str(history_id), "message": "Analyzing schema to find relevant tables..."})
            
            if settings.OPENROUTER_API_KEY:
                provider = OpenRouterProvider(
                    api_key=settings.OPENROUTER_API_KEY,
                    model="nvidia/nemotron-3-super-120b-a12b:free",
                )
            else:
                provider = OllamaProvider(
                    base_url=settings.OLLAMA_BASE_URL,
                    model=settings.OLLAMA_MODEL,
                    num_ctx=settings.OLLAMA_NUM_CTX,
                    keep_alive=settings.OLLAMA_KEEP_ALIVE,
                )
                
            logger.info(f"[{history_id}] Calling Brain Agent...")
            await manager.broadcast_to_session(str(session_id), {"type": "progress", "history_id": str(history_id), "message": "Analyzing intent..."})
            brain_agent = BrainAgent(llm_provider=provider)
            routing_plan = await brain_agent.run(user_query=message, history=history_list)
            logger.info(f"[{history_id}] Routing Plan: {routing_plan}")

            summary = None
            narrative = None
            chart_config = None
            sql_query = None
            results = None

            if not routing_plan.get("requires_data"):
                logger.info(f"[{history_id}] No data required. Using conversational response.")
                narrative = routing_plan.get("direct_response") or "I'm sorry, I cannot help with that."
                # We skip the rest of the pipeline
            else:
                logger.info(f"[{history_id}] Calling Schema Agent...")
                await manager.broadcast_to_session(str(session_id), {"type": "progress", "history_id": str(history_id), "message": "Analyzing schema to find relevant tables..."})
                
                schema_agent = SchemaAgent(llm_provider=provider)
                filtered_schema = await schema_agent.run(full_schema=schema, user_query=message, history=history_list)

                logger.info(f"[{history_id}] Calling SQL Agent...")
                await manager.broadcast_to_session(str(session_id), {"type": "progress", "history_id": str(history_id), "message": "Writing SQL query..."})
                agent = SQLAgent(llm_provider=provider)
                raw_sql = await agent.run(schema=filtered_schema, user_query=message, foreign_keys=foreign_keys, history=history_list)

                try:
                    sql_query = QueryValidator.validate_sql(raw_sql, dialect=conn.db_type)
                except QueryValidationError as qve:
                    raise Exception(f"Unsafe SQL generated: {qve.message}")

            # 4. Execute SQL
            if routing_plan.get("requires_data"):
                logger.info(f"[{history_id}] Executing generated SQL: {sql_query}")
                await manager.broadcast_to_session(str(session_id), {"type": "progress", "history_id": str(history_id), "message": "Executing SQL query..."})
                results = await connector.execute_query(sql_query)
                logger.info(f"[{history_id}] Query returned {len(results) if results else 0} rows.")

                # 5. Run Statistics, Narrator & Chart Agents
                if results:
                    if routing_plan.get("requires_stats"):
                        logger.info(f"[{history_id}] Calling Stats Agent...")
                        await manager.broadcast_to_session(str(session_id), {"type": "progress", "history_id": str(history_id), "message": "Analyzing results..."})
                        stats_agent = StatsAgent(llm_provider=provider)
                        summary = await stats_agent.run(user_query=message, raw_data=results)
                    
                    if routing_plan.get("requires_narrative"):
                        logger.info(f"[{history_id}] Calling Narrator Agent...")
                        await manager.broadcast_to_session(str(session_id), {"type": "progress", "history_id": str(history_id), "message": "Drafting executive summary..."})
                        narrator_agent = NarratorAgent(llm_provider=provider)
                        narrative = await narrator_agent.run(user_query=message, raw_data=results, stats_summary=summary)
                    
                    if routing_plan.get("requires_chart"):
                        logger.info(f"[{history_id}] Calling Chart Agent...")
                        await manager.broadcast_to_session(str(session_id), {"type": "progress", "history_id": str(history_id), "message": "Generating charts..."})
                        chart_agent = ChartAgent(llm_provider=provider)
                        chart_config = await chart_agent.run(user_query=message, raw_data=results)

            logger.info(f"[{history_id}] Pipeline completed successfully!")

            # 6. Update history as success
            stmt_hist = select(QueryHistory).where(QueryHistory.id == history_id)
            result_hist = await db.execute(stmt_hist)
            history_record = result_hist.scalar_one_or_none()
            
            if history_record:
                history_record.generated_sql = sql_query
                history_record.status = "success"
                history_record.result_row_count = len(results) if results else 0
                history_record.result_data = json.dumps(results[:10000], default=str) if results else "[]"
                history_record.result_summary = summary
                history_record.narrative = narrative
                if chart_config:
                    history_record.chart_config = json.dumps(chart_config, default=str)
                await db.commit()

            # Signal UI that processing is complete
            await manager.broadcast_to_session(str(session_id), {"type": "success", "history_id": str(history_id)})

            # Update session title if it's "New Chat"
            from app.models.chat_session import ChatSession
            stmt_sess = select(ChatSession).where(ChatSession.id == session_id)
            sess_res = await db.execute(stmt_sess)
            sess = sess_res.scalar_one_or_none()
            if sess and sess.title == "New Chat":
                sess.title = message[:40] + ("..." if len(message) > 40 else "")
                await db.commit()

        except Exception as exc:
            logger.error(f"[{history_id}] Pipeline failed: {str(exc)}")
            await db.rollback()
            # Update history as error
            stmt_hist = select(QueryHistory).where(QueryHistory.id == history_id)
            result_hist = await db.execute(stmt_hist)
            history_record = result_hist.scalar_one_or_none()
            
            if history_record:
                history_record.status = "error"
                history_record.error_message = str(exc)
                if 'raw_sql' in locals():
                    history_record.generated_sql = raw_sql
                await db.commit()
                
            await manager.broadcast_to_session(str(session_id), {"type": "error", "history_id": str(history_id), "message": str(exc)})


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
) -> ChatResponse:
    """
    Accept a chat query, save it as pending, and kick off background LLM worker.
    """
    # Verify connection exists first
    stmt = select(DatabaseConnection).where(
        DatabaseConnection.id == request.connection_id,
        DatabaseConnection.user_id == user.id,
    )
    result = await db.execute(stmt)
    conn = result.scalar_one_or_none()

    if conn is None:
        raise HTTPException(status_code=404, detail="Database connection not found")

    # Create pending history record
    history_record = QueryHistory(
        user_id=user.id,
        connection_id=conn.id,
        session_id=request.session_id,
        natural_language_query=request.message,
        generated_sql="", # FIX: Prevent NOT NULL constraint violation on existing DB schema
        status="pending",
    )
    db.add(history_record)
    await db.commit()
    await db.refresh(history_record)

    # Queue background task
    background_tasks.add_task(
        process_query_task,
        history_id=history_record.id,
        connection_id=conn.id,
        session_id=request.session_id,
        user_id=user.id,
        message=request.message
    )

    return ChatResponse(history_id=str(history_record.id), status="pending")


# ---------------------------------------------------------------------------
# GET /history/session/{session_id}
# ---------------------------------------------------------------------------
@router.get("/history/session/{session_id}")
async def get_chat_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    stmt = (
        select(QueryHistory)
        .where(
            QueryHistory.session_id == session_id,
            QueryHistory.user_id == user.id,
        )
        .order_by(QueryHistory.created_at.asc())
    )
    result = await db.execute(stmt)
    history = result.scalars().all()
    
    formatted_history = []
    for h in history:
        # Parse data safely
        data_rows = []
        if h.result_data:
            try:
                data_rows = json.loads(h.result_data)
            except:
                pass
        
        formatted_history.append({
            "id": str(h.id),
            "isUser": True,
            "text": h.natural_language_query,
            "sql": h.generated_sql,
            "data": data_rows if h.status == "success" else None,
            "summary": h.result_summary,
            "narrative": h.narrative,
            "chartConfig": json.loads(h.chart_config) if h.chart_config else None,
            "error": h.error_message,
            "status": h.status,
            "created_at": h.created_at,
        })
    return formatted_history

# ---------------------------------------------------------------------------
# DELETE /history/{history_id}
# ---------------------------------------------------------------------------
@router.delete("/history/{history_id}")
async def delete_chat_history(
    history_id: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    stmt = select(QueryHistory).where(
        QueryHistory.id == history_id,
        QueryHistory.user_id == user.id,
    )
    result = await db.execute(stmt)
    history_record = result.scalar_one_or_none()
    
    if not history_record:
        raise HTTPException(status_code=404, detail="History not found")
        
    await db.delete(history_record)
    await db.commit()
    return {"status": "deleted"}

# ---------------------------------------------------------------------------
# DELETE /history/connection/{connection_id}
# ---------------------------------------------------------------------------
@router.delete("/history/connection/{connection_id}")
async def clear_chat_history(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    stmt = delete(QueryHistory).where(
        QueryHistory.connection_id == connection_id,
        QueryHistory.user_id == user.id,
    )
    await db.execute(stmt)
    await db.commit()
    return {"status": "cleared"}
