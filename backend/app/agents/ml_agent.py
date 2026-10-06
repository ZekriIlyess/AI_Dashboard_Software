from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)

ML_SYSTEM_PROMPT = """You are the AutoML Orchestration Agent for Nexus AI.
Your job is to analyze a dataset summary and a user question, and recommend the best Machine Learning pipeline.

The available pipelines are:
1. "classification" (for predicting discrete target classes, e.g. churn, fraud)
2. "regression" (for predicting continuous target variables, e.g. price, sales)
3. "time_series" (for forecasting values over time, e.g. demand forecasting)
4. "anomaly" (for identifying outliers/anomalies in data)
5. "causal" (for estimating the causal effect of a treatment variable on an outcome)
6. "none" (if ML is not suitable or needed)

You must respond in strict JSON format matching this schema:
{
    "suggested_task": "classification" | "regression" | "time_series" | "anomaly" | "causal" | "none",
    "reasoning": "A concise explanation of why this technique is recommended",
    "parameters": {
        "target_column": "Name of target column to predict (required for classification, regression, time_series)",
        "date_column": "Name of the time/date column (required for time_series)",
        "treatment_column": "Name of treatment column (required for causal)",
        "outcome_column": "Name of outcome column (required for causal)",
        "common_causes": ["List of confounding control columns (for causal)"]
    }
}
"""

ML_USER_PROMPT = """Dataset Summary:
{data_summary}

User Question:
{user_question}

Analyze the information above and return your ML recommendation in JSON.
"""

class MLAgent:
    """Agent that handles AutoML routing, task selection, and hyperparameter suggestions."""

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

    async def suggest_analysis(
        self,
        data_summary: str,
        user_question: str
    ) -> Dict[str, Any]:
        """Ask LLM to recommend the optimal ML technique."""
        try:
            user_prompt = ML_USER_PROMPT.format(
                data_summary=data_summary,
                user_question=user_question
            )

            raw_response: str = await self._provider.generate(
                ML_SYSTEM_PROMPT,
                user_prompt,
                json_mode=True
            )
            parsed = self._extract_json_object(raw_response)

            if parsed:
                return {
                    "suggested_task": parsed.get("suggested_task", "none"),
                    "reasoning": parsed.get("reasoning", "No reasoning provided"),
                    "parameters": parsed.get("parameters", {})
                }
        except Exception as e:
            logger.error(f"MLAgent failed to suggest analysis: {e}")

        # Fallback
        return {
            "suggested_task": "none",
            "reasoning": "Fallback routing due to LLM error or parse failure",
            "parameters": {}
        }
