from __future__ import annotations

import json
from typing import Dict, Any

import httpx

class OllamaProvider:
    """
    A thin wrapper around a local Ollama server that can generate SQL from a JSON schema.
    """

    def __init__(self, base_url: str, model: str, num_ctx: int = 32768, keep_alive: str = "2h") -> None:
        self.base_url = base_url.rstrip("/")
        if not self.base_url.startswith("http://") and not self.base_url.startswith("https://"):
            self.base_url = f"http://{self.base_url}"
        self.model = model
        self.num_ctx = num_ctx
        self.keep_alive = keep_alive

    async def generate(self, system: str, user: str, json_mode: bool = False) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": f"{system}\n\n{user}",
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {
                "num_ctx": self.num_ctx,
                "num_predict": -1
            }
        }
        
        # We explicitly do NOT pass "format": "json" to Ollama here.
        # Local 30B models in Ollama often hang or crash when forced into strict JSON FSM grammars.
        # Our robust prompts and regex extraction already guarantee perfect JSON parsing.

        url = f"{self.base_url}/api/generate"

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=None)

        try:
            response.raise_for_status()
        except Exception as exc:
            raise RuntimeError(f"Ollama request failed ({response.status_code}): {response.text}") from exc

        data = response.json()

        raw_text = data.get("response", "")
        if not raw_text:
            raise RuntimeError("Empty response from Ollama")

        return raw_text
