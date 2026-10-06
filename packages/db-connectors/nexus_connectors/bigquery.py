from __future__ import annotations

import asyncio
from typing import List, Dict, Any

from google.cloud import bigquery

from .base import BaseConnector

class BigQueryConnector(BaseConnector):
    """
    A BigQuery connector that wraps the synchronous driver with `asyncio.to_thread`.
    """

    def __init__(
        self,
        host: str, # Service Account JSON path
        project_id: str,
        *,
        default_dataset: str | None = None,
        location: str = "US",
    ):
        super().__init__(host=host, database=project_id)
        self.service_account_path = host
        self.project_id = project_id
        self.dataset_id = default_dataset
        self.location = location

        try:
            self.client = bigquery.Client.from_service_account_json(self.service_account_path)
        except Exception:
            self.client = None # For testing without a real key file

    def _run_and_fetch(self, query: str):
        if not self.client:
            raise RuntimeError("BigQuery client not initialized (missing valid service account JSON).")
        job = self.client.query(query, default_timeout=30.0)
        return job.result()

    async def test_connection(self) -> bool:
        def _test():
            try:
                if self.dataset_id:
                    for _ in self.client.list_datasets(self.project_id):
                        pass
                    return True
                result = self._run_and_fetch("SELECT * FROM `bigquery-public-data.usa_names.usa_1910_current` LIMIT 1")
                return bool(next(result, None))
            except Exception:
                return False
        return await asyncio.to_thread(_test)

    async def execute_query(self, query: str) -> List[Dict[str, Any]]:
        def _exec():
            rows = self._run_and_fetch(query)
            col_names = [field.name for field in rows.context.row_type.fields]
            return [{col_name: value for col_name, value in zip(col_names, row)} for row in rows]
        return await asyncio.to_thread(_exec)

    async def get_schema(self) -> Dict[str, List[Dict[str, str]]]:
        def _schema():
            schema_dict: Dict[str, List[Dict[str, str]]] = {}
            region = self.location if self.location.upper() == "US" else f"{self.location.upper()}"
            
            if self.dataset_id:
                table_query = f"SELECT TABLE_NAME FROM `{self.project_id}`.{self.dataset_id}.INFORMATION_SCHEMA.TABLES WHERE IS_VIEW = FALSE"
            else:
                table_query = f"SELECT TABLE_NAME FROM `{self.project_id}`.region-{region}.INFORMATION_SCHEMA.TABLES WHERE IS_VIEW = FALSE"
                
            try:
                results = self._run_and_fetch(table_query)
                all_tables = [row["TABLE_NAME"] for row in results]
            except Exception:
                return {}

            for tbl_name in all_tables:
                col_meta_query = f"""
                    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
                    FROM `{self.project_id}`.{self.dataset_id or f'region-{region}'}.INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = '{tbl_name}'
                    ORDER BY ORDINAL_POSITION
                """
                try:
                    cols_res = self._run_and_fetch(col_meta_query)
                    col_descr = []
                    for row in cols_res:
                        col_descr.append({
                            "name": row["COLUMN_NAME"],
                            "type": row["DATA_TYPE"].lower(),
                            "not_null": "NO" if row["IS_NULLABLE"] == "YES" else "YES",
                            "default": "",
                            "extra": "",
                        })
                    schema_dict[tbl_name] = col_descr
                except Exception:
                    continue

            return schema_dict
        return await asyncio.to_thread(_schema)

    async def get_foreign_keys(self) -> List[Dict[str, str]]:
        # BigQuery does not strongly enforce/expose FKs natively via INFORMATION_SCHEMA
        return []
