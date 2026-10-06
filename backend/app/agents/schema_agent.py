from __future__ import annotations

import json
import re
from typing import Any, Dict

from .llm.prompts.schema_analysis import SCHEMA_SYSTEM_PROMPT, SCHEMA_USER_PROMPT

class SchemaAgent:
    def __init__(self, llm_provider: Any) -> None:
        self._provider = llm_provider

    @staticmethod
    def _extract_json_list(text: str) -> list[str] | None:
        text = re.sub(r"```(?:\w+)?\s*", "", text, flags=re.DOTALL).strip()
        try:
            parsed: Any = json.loads(text)
        except json.JSONDecodeError:
            import ast
            try:
                parsed = ast.literal_eval(text)
            except Exception:
                return None
                
        if isinstance(parsed, dict) and "tables" in parsed:
            tables_list = parsed["tables"]
            if isinstance(tables_list, list):
                try:
                    return [str(item) for item in tables_list]
                except Exception:
                    return None
        elif isinstance(parsed, list):
            # Fallback in case the LLM still returns an array directly
            try:
                return [str(item) for item in parsed]
            except Exception:
                return None
        return None

    @staticmethod
    def _format_history(history: list[Dict[str, str]]) -> str:
        if not history:
            return "No previous history."
        lines = []
        for entry in history:
            user_q = (entry.get("user_query") or "").strip()
            sql_stmt = (entry.get("sql") or "").strip()
            if user_q:
                lines.append(f"User: {user_q}")
            if sql_stmt:
                lines.append(f"Assistant: ```sql\n{sql_stmt}\n```")
        return "\n".join(lines)

    async def run(
        self,
        full_schema: Dict[str, Any],
        user_query: str,
        history: list[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if history is None:
            history = []
            
        system_prompt = SCHEMA_SYSTEM_PROMPT
        schema_json = json.dumps(full_schema, ensure_ascii=False, indent=2)
        formatted_history = self._format_history(history)
        
        user_prompt = SCHEMA_USER_PROMPT.format(
            schema=f"```json\n{schema_json}\n```",
            user_query=user_query,
            history_text=formatted_history,
        )

        raw_response: str = await self._provider.generate(system_prompt, user_prompt, json_mode=True)
        extracted_tables = self._extract_json_list(raw_response)

        if not isinstance(extracted_tables, list):
            return full_schema

        selected: Dict[str, Any] = {
            name: metadata for name, metadata in full_schema.items()
            if name in extracted_tables
        }

        return selected
