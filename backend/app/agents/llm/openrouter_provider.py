from __future__ import annotations
import json
from openai import AsyncOpenAI

class OpenRouterProvider:
    """
    A thin wrapper around the OpenRouter API that conforms to the same interface as OllamaProvider.
    """

    def __init__(self, api_key: str, model: str) -> None:
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.model = model

    async def generate(self, system: str, user: str, json_mode: bool = False) -> str:
        try:
            kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ]
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
                
            response = await self.client.chat.completions.create(**kwargs)
            raw_text = response.choices[0].message.content
            if not raw_text:
                raise RuntimeError("Empty response from OpenRouter")
            return raw_text
        except Exception as exc:
            raise RuntimeError(f"OpenRouter request failed: {str(exc)}") from exc
