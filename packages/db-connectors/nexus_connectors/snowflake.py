from __future__ import annotations

import asyncio
from typing import List, Dict, Any

import snowflake.connector

from .base import BaseConnector

class SnowflakeConnector(BaseConnector):
    """
    A Snowflake connector that wraps the synchronous driver with `asyncio.to_thread`
    so it does not block the main event loop.
    """

    def __init__(
        self,
        account: str,
        user: str,
        password: str,
        *,
        warehouse: str = "COMPUTE_WH",
        database: str | None = None,
        schema: str | None = None,
        role: str | None = None,
    ):
        super().__init__(host=account, database=database, user=user, password=password)
        self.account = account
        self.warehouse = warehouse
        self.schema = schema
        self.role = role

        self._conn_kwargs: Dict[str, Any] = {
            "account": account,
            "user": user,
            "password": password,
            "warehouse": warehouse,
            "database": database,
            "schema": schema,
            "role": role,
        }

    def _get_connection(self):
        return snowflake.connector.connect(**self._conn_kwargs)

    async def test_connection(self) -> bool:
        def _test():
            try:
                with self._get_connection() as ctx:
                    with ctx.cursor() as cur:
                        cur.execute("SELECT 1")
                        row = cur.fetchone()
                        return row is not None and int(row[0]) == 1
            except Exception:
                return False
        return await asyncio.to_thread(_test)

    async def execute_query(self, query: str) -> List[Dict[str, Any]]:
        def _exec():
            with self._get_connection() as ctx:
                with ctx.cursor() as cur:
                    cur.execute(query)
                    col_names = [d[0] for d in cur.description]
                    rows = cur.fetchall()
                    return [{col: row[i] for i, col in enumerate(col_names)} for row in rows]
        return await asyncio.to_thread(_exec)

    async def get_schema(self) -> Dict[str, List[Dict[str, str]]]:
        def _schema():
            schema_dict: Dict[str, List[Dict[str, str]]] = {}
            with self._get_connection() as ctx:
                with ctx.cursor() as cur:
                    cur.execute(
                        "SELECT DISTINCT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_CATALOG = %s",
                        (self.database,)
                    )
                    tables = [r[0] for r in cur.fetchall()]

            for tbl_name in tables:
                with self._get_connection() as ctx:
                    with ctx.cursor() as cur:
                        cur.execute(
                            """
                            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
                            FROM INFORMATION_SCHEMA.COLUMNS
                            WHERE TABLE_CATALOG = %s AND TABLE_NAME = %s
                            ORDER BY ORDINAL_POSITION
                            """,
                            (self.database, tbl_name),
                        )
                        cols = []
                        for col_name, data_type, is_nullable, max_len in cur.fetchall():
                            cols.append({
                                "name": col_name,
                                "type": data_type.lower(),
                                "not_null": "NO" if is_nullable == "YES" else "YES",
                                "default": "",
                                "extra": "",
                            })
                        schema_dict[tbl_name] = cols
            return schema_dict
        return await asyncio.to_thread(_schema)

    async def get_foreign_keys(self) -> List[Dict[str, str]]:
        def _fks():
            fks = []
            with self._get_connection() as ctx:
                with ctx.cursor() as cur:
                    cur.execute(
                        """
                        SELECT CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                        FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS
                        WHERE TABLE_CATALOG = %s
                        """,
                        (self.database,)
                    )
                    for cons_name, tbl, col, ref_tbl, ref_col in cur.fetchall():
                        fks.append({
                            "table_name": tbl,
                            "column_name": col,
                            "foreign_table_name": ref_tbl or "",
                            "foreign_column_name": ref_col or "",
                        })
            return fks
        return await asyncio.to_thread(_fks)
