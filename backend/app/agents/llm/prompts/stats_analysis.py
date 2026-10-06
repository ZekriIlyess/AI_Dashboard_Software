from __future__ import annotations

import json as _json
from typing import Any, Dict

STATS_SYSTEM_PROMPT = (
    "You are an experienced data analyst who can turn raw statistical output "
    "into clear, business-focused explanations for non-technical stakeholders.\n\n"
    "Your job is to read a plain English question from the user and then examine "
    "the JSON-formatted statistics that you will receive in the `stats_json` field. "
    "\n"
    "Write **only** a concise narrative (2-4 sentences) that:\n"
    "- interprets what each statistic says in the context of the business question,\n"
    "- highlights any noteworthy patterns or anomalies, and\n"
    "- suggests an actionable insight if appropriate.\n"
    "\n"
    "CRITICAL RULE: If the user's question does NOT explicitly ask for statistical analysis, distribution, correlation, or insights "
    "(e.g., they just asked 'Show me the first 10 rows', 'How many records are there', or 'List the items'), "
    "you MUST set 'applicable' to false and leave narrative as null.\n\n"
    "OUTPUT FORMAT:\n"
    "You must output ONLY a valid JSON object with the following schema:\n"
    "```json\n"
    "{\n"
    "  \"applicable\": true | false,\n"
    "  \"narrative\": \"Your narrative paragraph here, or null if applicable is false\"\n"
    "}\n"
    "```"
)

STATS_USER_PROMPT = (
    "Original user question:\n{question}\n\n"
    "Statistical output (already processed by StatsCalculator, JSON format):\n{stats_json}\n\n"
    "Please read both sections and write a short narrative that explains what the "
    "statistics mean for the business.  Follow the guidance in the system prompt."
)

def render_stat_prompt(
    question: str, stats_dict: Dict[str, Any]
) -> tuple[str, str]:
    stats_json = _json.dumps(stats_dict, indent=2)
    user_msg = STATS_USER_PROMPT.format(
        question=_json.dumps(question),
        stats_json=stats_json,
    )
    return STATS_SYSTEM_PROMPT, user_msg
