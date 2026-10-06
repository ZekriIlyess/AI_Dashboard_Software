from __future__ import annotations

import logging
from typing import Any, Dict

from app.config import settings
from app.agents.llm.local_provider import OllamaProvider
from app.agents.llm.openrouter_provider import OpenRouterProvider

logger = logging.getLogger(__name__)

class LLMRouter:
    """Routes requests to the optimal LLM provider based on task type and strategy."""

    def __init__(self) -> None:
        self.providers: Dict[str, Any] = {}

        # 1. Setup primary local provider (always available)
        self.providers["local_primary"] = OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            num_ctx=settings.OLLAMA_NUM_CTX,
            keep_alive=settings.OLLAMA_KEEP_ALIVE
        )

        # 2. Setup secondary local provider (optional)
        if settings.OLLAMA_SECONDARY_BASE_URL and settings.OLLAMA_SECONDARY_MODEL:
            self.providers["local_secondary"] = OllamaProvider(
                base_url=settings.OLLAMA_SECONDARY_BASE_URL,
                model=settings.OLLAMA_SECONDARY_MODEL,
                num_ctx=settings.OLLAMA_NUM_CTX,
                keep_alive=settings.OLLAMA_KEEP_ALIVE
            )
        else:
            self.providers["local_secondary"] = self.providers["local_primary"]

        # 3. Setup OpenRouter provider (optional)
        if settings.OPENROUTER_API_KEY:
            # We assume a default cloud model if none is specified or config doesn't list one
            # E.g. meta-llama/llama-3-70b-instruct or anthropic/claude-3-haiku
            cloud_model = "meta-llama/llama-3-70b-instruct:free"
            self.providers["openrouter"] = OpenRouterProvider(
                api_key=settings.OPENROUTER_API_KEY,
                model=cloud_model
            )

    def get_provider(self, task: str) -> Any:
        """Get the appropriate provider for the specified task."""
        strategy = settings.LLM_ROUTER_STRATEGY.lower()

        # If local_only, force Ollama
        if strategy == "local_only" or "openrouter" not in self.providers:
            if task == "batch_inference":
                return self.providers["local_secondary"]
            return self.providers["local_primary"]

        # Hybrid routing rules
        if task == "batch_inference":
            return self.providers["local_secondary"]
        
        # In cloud_hybrid mode, we offload reasoning-heavy tasks to cloud OpenRouter
        if task in ("schema_analysis", "sql_generation", "ml_suggestion"):
            return self.providers["openrouter"]
            
        return self.providers["local_primary"]
