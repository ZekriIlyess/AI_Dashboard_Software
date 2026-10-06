from __future__ import annotations

import json
import re
from typing import Any, Dict

from .llm.prompts.brain_routing import BRAIN_SYSTEM_PROMPT, BRAIN_USER_PROMPT

class BrainAgent:
    def __init__(self, llm_provider: Any) -> None:
        self._provider = llm_provider

    @staticmethod
    def _extract_json_object(text: str) -> Dict[str, Any] | None:
        text = re.sub(r"```(?:\w+)?\s*", "", text, flags=re.DOTALL).strip()
        try:
            parsed: Any = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        return None

    @staticmethod
    def _format_history(history: list[Dict[str, str]]) -> str:
        if not history:
            return "No previous history."
        lines = []
        for entry in history:
            user_q = (entry.get("user_query") or "").strip()
            # Try to grab whatever assistant returned (narrative or direct response)
            assistant_reply = entry.get("narrative", "") or entry.get("direct_response", "") or ""
            if user_q:
                lines.append(f"User: {user_q}")
            if assistant_reply:
                lines.append(f"Assistant: {assistant_reply}")
        return "\n".join(lines)

    async def run(
        self,
        user_query: str,
        history: list[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if history is None:
            history = []
            
        system_prompt = BRAIN_SYSTEM_PROMPT
        formatted_history = self._format_history(history)
        
        user_prompt = BRAIN_USER_PROMPT.format(
            history_text=formatted_history,
            user_query=user_query,
        )

        raw_response: str = await self._provider.generate(system_prompt, user_prompt, json_mode=True)
        parsed = self._extract_json_object(raw_response)

        # Fallback defaults if LLM hallucinates or fails to return JSON
        if not parsed:
            return {
                "requires_data": True,
                "direct_response": None,
                "requires_stats": False,
                "requires_chart": False,
                "requires_narrative": False
            }

        return {
            "requires_data": bool(parsed.get("requires_data", True)),
            "direct_response": parsed.get("direct_response"),
            "requires_stats": bool(parsed.get("requires_stats", False)),
            "requires_chart": bool(parsed.get("requires_chart", False)),
            "requires_narrative": bool(parsed.get("requires_narrative", False))
        }
