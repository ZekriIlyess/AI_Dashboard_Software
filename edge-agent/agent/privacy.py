from __future__ import annotations

import re
from typing import Any, Dict, List, Set

class PIIMasker:
    """Detects and redacts Personally Identifiable Information (PII) from query datasets."""

    EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    PHONE_REGEX = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
    SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    CREDIT_CARD_REGEX = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def mask_dataset(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Scan a list of row dicts and mask detected PII fields."""
        if not self.enabled or not data:
            return data

        # 1. Identify columns that look like PII from names
        pii_columns: Set[str] = set()
        sample_row = data[0]

        for col in sample_row.keys():
            col_lower = col.lower()
            if any(term in col_lower for term in ("email", "phone", "ssn", "social_security", "credit_card", "cc_num", "password", "secret", "cvv")):
                pii_columns.add(col)

        # 2. Process all rows and redact values
        masked_data = []
        for row in data:
            new_row = {}
            for col, val in row.items():
                if val is None:
                    new_row[col] = None
                    continue

                val_str = str(val)

                # Redact if name matches
                if col in pii_columns:
                    new_row[col] = self._mask_value(col.lower(), val_str)
                    continue

                # Scan content with Regex for safety even if column name is generic
                if isinstance(val, str):
                    val_str = self._scan_and_mask_content(val_str)

                new_row[col] = val_str
            masked_data.append(new_row)

        return masked_data

    def _mask_value(self, col_name: str, value: str) -> str:
        """Apply targeted mask format based on column classification."""
        if "email" in col_name:
            parts = value.split("@")
            if len(parts) == 2:
                name, domain = parts
                masked_name = name[:2] + "***" if len(name) > 2 else "***"
                return f"{masked_name}@{domain}"
            return "[EMAIL_MASKED]"
        elif "phone" in col_name:
            return re.sub(r"\d", "*", value)[:-4] + value[-4:] if len(value) > 4 else "****"
        elif "ssn" in col_name or "social" in col_name:
            return "***-**-" + value[-4:] if len(value) >= 4 else "[SSN_MASKED]"
        elif "card" in col_name or "cc_" in col_name:
            return "****-****-****-" + value[-4:] if len(value) >= 4 else "[CARD_MASKED]"
        else:
            return "[REDACTED]"

    def _scan_and_mask_content(self, text: str) -> str:
        """Scan generic string content with regexes and replace PII blocks."""
        text = self.EMAIL_REGEX.sub("[EMAIL_REDACTED]", text)
        text = self.PHONE_REGEX.sub("[PHONE_REDACTED]", text)
        text = self.SSN_REGEX.sub("[SSN_REDACTED]", text)
        text = self.CREDIT_CARD_REGEX.sub("[CARD_REDACTED]", text)
        return text
