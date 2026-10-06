from __future__ import annotations

import asyncio
import logging
import httpx

from agent.config import settings
from agent.executor import QueryExecutor
from agent.privacy import PIIMasker

logger = logging.getLogger(__name__)

class CloudTunnel:
    """Manages secure outbound communication with the central cloud control plane."""

    def __init__(self):
        self.executor = QueryExecutor()
        self.masker = PIIMasker(enabled=settings.PII_MASKING_ENABLED)
        self.client = httpx.AsyncClient(base_url=settings.CLOUD_PLATFORM_URL)
        self.agent_uuid = settings.AGENT_UUID
        self._running = False

    async def start(self):
        """Start the background poll loop."""
        self._running = True
        logger.info(f"Starting cloud tunnel coordinator for agent {self.agent_uuid}...")
        
        while self._running:
            try:
                await self._poll_and_execute()
            except Exception as e:
                logger.error(f"Error in cloud tunnel poll cycle: {e}")
            
            await asyncio.sleep(settings.POLL_INTERVAL_SECONDS)

    def stop(self):
        """Stop poll loop."""
        self._running = False

    async def _poll_and_execute(self):
        """Fetch pending execution jobs, execute, mask, and send results back."""
        # Note: If no cloud connection is configured or if we use local REST mode, skip polling
        if self.agent_uuid == "00000000-0000-0000-0000-000000000000":
            return

        url = f"/api/agent-jobs/poll/{self.agent_uuid}"
        try:
            response = await self.client.get(url, timeout=5.0)
            if response.status_code == 204 or response.status_code == 404:
                return # No jobs available

            if response.status_code == 200:
                job = response.json()
                job_id = job.get("id")
                query = job.get("query")
                
                logger.info(f"Received job {job_id} from cloud. Executing...")
                
                try:
                    # 1. Execute SQL
                    raw_data = await self.executor.execute(query)
                    
                    # 2. Mask PII
                    clean_data = self.masker.mask_dataset(raw_data)
                    
                    # 3. Report Success
                    await self.client.post(
                        f"/api/agent-jobs/complete/{job_id}",
                        json={"status": "success", "data": clean_data},
                        timeout=10.0
                    )
                    logger.info(f"Job {job_id} completed and uploaded.")
                    
                except Exception as run_error:
                    logger.error(f"Failed to execute job {job_id}: {run_error}")
                    await self.client.post(
                        f"/api/agent-jobs/complete/{job_id}",
                        json={"status": "failed", "error": str(run_error)},
                        timeout=5.0
                    )
        except httpx.RequestError as exc:
            logger.debug(f"Cloud coordinator unavailable: {exc}")
