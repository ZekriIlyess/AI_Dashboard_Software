from __future__ import annotations

import json
from typing import Any, List, Dict
from app.core.statistics import StatsCalculator
from .llm.prompts.stats_analysis import render_stat_prompt

class StatsAgent:
    """
    Analyzes raw SQL data using pandas and generates a plain-English 
    business narrative interpreting the statistics.
    """
    def __init__(self, llm_provider: Any) -> None:
        self._provider = llm_provider

    async def run(self, user_query: str, raw_data: List[Dict]) -> str | None:
        if not raw_data:
            return None
            
        sample_rows = raw_data[:5]
        sample_json = json.dumps(sample_rows, ensure_ascii=False, indent=2, default=str)
        first_row = raw_data[0]
        numeric_cols = []
        for col, val in first_row.items():
            if isinstance(val, (int, float)):
                numeric_cols.append(col)
                
        if len(numeric_cols) == 0:
            return None
            
        stats_dict = {}
        
        try:
            if len(numeric_cols) >= 2:
                col1, col2 = numeric_cols[0], numeric_cols[1]
                stats_dict = StatsCalculator.calculate_correlation(raw_data, col1, col2)
                stats_dict["analysis_type"] = f"Pearson correlation between '{col1}' and '{col2}'"
            else:
                col = numeric_cols[0]
                stats_dict = StatsCalculator.calculate_distribution(raw_data, col)
                stats_dict["analysis_type"] = f"Distribution analysis of '{col}'"
                
            sys_prompt, usr_prompt = render_stat_prompt(user_query, stats_dict)
            raw_response = await self._provider.generate(sys_prompt, usr_prompt, json_mode=True)
            
            # Clean up potential markdown formatting
            import re
            cleaned = raw_response.strip()
            cleaned = re.sub(r"^(```|\"\"\")[jJ][sS][oO][nN]\s*", "", cleaned)
            cleaned = re.sub(r"^(```|\"\"\")\s*", "", cleaned)
            if cleaned.endswith("```") or cleaned.endswith('"""'):
                cleaned = cleaned[:-3].strip()
                
            try:
                parsed = json.loads(cleaned)
                if not parsed.get("applicable", False):
                    return None
                return parsed.get("narrative")
            except (json.JSONDecodeError, ValueError):
                return None
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"StatsAgent Error: {e}")
            return None
