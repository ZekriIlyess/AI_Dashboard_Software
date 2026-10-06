from __future__ import annotations

import json
from typing import Any, List, Dict
from app.agents.llm.prompts.narration import NARRATION_SYSTEM_PROMPT, NARRATION_USER_PROMPT

class NarratorAgent:
    """
    Takes raw SQL results and statistical analysis, and generates a premium, 
    plain-English executive summary highlighting actionable insights.
    """
    def __init__(self, llm_provider: Any) -> None:
        self._provider = llm_provider

    async def run(self, user_query: str, raw_data: List[Dict], stats_summary: str | None) -> str | None:
        if not raw_data:
            return None
            
        sample_rows = raw_data[:5]
        data_snapshot = json.dumps(sample_rows, ensure_ascii=False, indent=2, default=str)
        stats_text = stats_summary if stats_summary else "No advanced statistical correlations identified."
        
        user_prompt = NARRATION_USER_PROMPT.format(
            user_query=user_query,
            data_snapshot=data_snapshot,
            stats_summary=stats_text
        )
        
        try:
            narrative = await self._provider.generate(NARRATION_SYSTEM_PROMPT, user_prompt)
            if narrative.strip().upper() == "NULL":
                return None
            return narrative
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"NarratorAgent Error: {e}")
            return None
