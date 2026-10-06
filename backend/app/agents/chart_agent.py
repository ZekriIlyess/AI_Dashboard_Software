import json
import re
from typing import List, Dict, Any, Optional

from .llm.prompts.chart_generation import CHART_SYSTEM_PROMPT, CHART_USER_PROMPT

class ChartAgent:
    """
    Async chart‑generation agent.
    """

    def __init__(self, llm_provider: Any):
        self.llm_provider = llm_provider

    async def run(
        self,
        user_query: str,
        raw_data: List[Dict[str, Any]],
    ) -> Optional[Dict[str, str]]:
        if not raw_data:
            return None

        sample_rows = raw_data[:5]
        sample_json = json.dumps(sample_rows, ensure_ascii=False, indent=2, default=str)

        # Collect up to 50 unique values for each string column
        unique_vals_info = {}
        if raw_data:
            string_cols = {k: set() for k, v in raw_data[0].items() if isinstance(v, str)}
            for row in raw_data:
                for k in string_cols:
                    if isinstance(row.get(k), str):
                        string_cols[k].add(row[k])
            
            for k, v in string_cols.items():
                if len(v) <= 50:
                    unique_vals_info[k] = list(v)
                else:
                    unique_vals_info[k] = list(v)[:50] + ["..."]

        user_prompt_filled = CHART_USER_PROMPT.format(
            user_query=user_query,
            total_rows=len(raw_data),
            sample_data=sample_json,
            unique_values=json.dumps(unique_vals_info, ensure_ascii=False, indent=2, default=str)
        )

        llm_response_text = await self.llm_provider.generate(CHART_SYSTEM_PROMPT, user_prompt_filled, json_mode=True)
        
        # Clean up potential markdown formatting
        cleaned = llm_response_text.strip()
        cleaned = re.sub(r"^(```|\"\"\")[jJ][sS][oO][nN]\s*", "", cleaned)
        cleaned = re.sub(r"^(```|\"\"\")\s*", "", cleaned)
        if cleaned.endswith("```") or cleaned.endswith('"""'):
            cleaned = cleaned[:-3].strip()

        try:
            chart_spec: Dict[str, str] = json.loads(cleaned)
            chart_type = chart_spec.get("type")
            
            if not isinstance(chart_type, str) or chart_type.lower() == "none" or not chart_type:
                return None

            # Validate that x and y exist in the raw_data
            x_key = chart_spec.get("x")
            y_key = chart_spec.get("y")
            
            if x_key and x_key not in raw_data[0]:
                return None
                
            if y_key and y_key not in raw_data[0]:
                return None
                
            # Validate that y is actually numeric (if it exists)
            if y_key:
                val = raw_data[0][y_key]
                if not isinstance(val, (int, float)):
                    # Check if it can be parsed as float
                    try:
                        if val is not None:
                            float(val)
                    except (ValueError, TypeError):
                        return None

            return chart_spec
        except (json.JSONDecodeError, ValueError) as exc:
            return None
