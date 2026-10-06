from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from agent.config import settings
from agent.executor import QueryExecutor
from agent.privacy import PIIMasker
from agent.tunnel import CloudTunnel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("nexus-edge-agent")

tunnel = CloudTunnel()
executor = QueryExecutor()
masker = PIIMasker(enabled=settings.PII_MASKING_ENABLED)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start outbound poll coordinator in the background
    task = asyncio.create_task(tunnel.start())
    logger.info("Nexus Edge Agent started.")
    yield
    # Cleanup on shutdown
    tunnel.stop()
    await task
    logger.info("Nexus Edge Agent shut down.")

app = FastAPI(
    title="Nexus AI Edge Agent",
    version="0.1.0",
    lifespan=lifespan
)

# ---------- Schemas ----------

class QueryRequest(BaseModel):
    query: str

# ---------- Endpoints ----------

@app.get("/health")
def health_check():
    """Health check for Docker orchestrator."""
    return {"status": "healthy", "agent_uuid": settings.AGENT_UUID}


@app.post("/execute")
async def execute_query(request: QueryRequest):
    """Direct REST SQL execution (for local private network query routing)."""
    try:
        raw_data = await executor.execute(request.query)
        clean_data = masker.mask_dataset(raw_data)
        return {"status": "success", "data": clean_data}
    except Exception as exc:
        logger.error(f"Execution error over REST: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        )
