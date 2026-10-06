from __future__ import annotations

import re
from typing import Dict, Any, List

from .llm.prompts.sql_generation import SQL_SYSTEM_PROMPT, SQL_USER_PROMPT
import json

class SQLAgent:
    """
    Thin façade that uses an OllamaProvider (or any compatible LLM provider) to turn a
    JSON schema plus a natural language request into executable PostgreSQL code.
    """

    _MARKDOWN_FENCE_RE = re.compile(r"```(sql)?\s*")

    def __init__(self, llm_provider: Any) -> None:
        self._provider = llm_provider

    @staticmethod
    def _format_history(history: List[Dict[str, str]]) -> str:
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

    async def run(self, schema: Dict[Any, Any], user_query: str, foreign_keys: List[Dict[str, str]] = None, history: List[Dict[str, str]] = None) -> str:
        if foreign_keys is None:
            foreign_keys = []
            
        system_prompt = SQL_SYSTEM_PROMPT
        schema_json = json.dumps(schema, ensure_ascii=False, indent=2)
        fk_json = json.dumps(foreign_keys, ensure_ascii=False, indent=2)
        formatted_history = self._format_history(history)
        
        user_prompt = SQL_USER_PROMPT.format(
            filtered_schema=schema_json,
            user_query=user_query,
            foreign_keys_json=fk_json,
            history_text=formatted_history,
        )

        raw_sql = await self._provider.generate(system_prompt, user_prompt)

        # Remove optional markdown fencing
        cleaned = raw_sql.strip()
        
        # If the LLM wrapped it in ```sql ... ``` anywhere in the text, extract just that part
        match = re.search(r"```[sS][qQ][lL]?\s*(.*?)\s*```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
        else:
            # Fallback: Strip leading code block markers if it didn't close properly
            cleaned = re.sub(r"^(```|\"\"\")[sS][qQ][lL]\s*", "", cleaned)
            cleaned = re.sub(r"^(```|\"\"\")\s*", "", cleaned)
            if cleaned.endswith("```") or cleaned.endswith('"""'):
                cleaned = cleaned[:-3].strip()
                
        return cleaned
