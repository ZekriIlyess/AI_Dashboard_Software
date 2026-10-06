from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import anyio
import pymssql

from .base import BaseConnector

logger = logging.getLogger(__name__)

class SQLServerConnector(BaseConnector):
    """
    SQL Server Database Connector using ``pymssql`` executed in a thread pool.
    """

    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 1433,
        user: str = "sa",
        password: str = "",
        database: str = "",
    ) -> None:
        super().__init__(host=host, port=port, database=database, user=user, password=password)

    def _connect(self) -> pymssql.Connection:
        """Establish synchronous connection."""
        return pymssql.connect(
            server=self.host,
            port=str(self.port),
            user=self.user,
            password=self.password,
            database=self.database,
            autocommit=True
        )

    async def test_connection(self) -> bool:
        """Test connection asynchronously."""
        def _test():
            try:
                conn = self._connect()
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    row = cur.fetchone()
                    return bool(row and row[0] == 1)
            except Exception:
                return False

        return await anyio.to_thread.run_sync(_test)

    async def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Run SQL query in a background thread."""
        def _execute():
            conn = self._connect()
            with conn.cursor(as_dict=True) as cur:
                cur.execute(query)
                # pymssql cursors raise exception on fetchall() if query returns no rows (e.g. INSERT)
                try:
                    rows = cur.fetchall()
                    return list(rows) if rows else []
                except Exception:
                    return []

        return await anyio.to_thread.run_sync(_execute)

    async def get_schema(self) -> Dict[str, List[Dict[str, str]]]:
        """Fetch database schema."""
        def _get_schema():
            conn = self._connect()
            schema: Dict[str, List[Dict[str, str]]] = {}
            with conn.cursor(as_dict=True) as cur:
                cur.execute(
                    """
                    SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                    FROM INFORMATION_SCHEMA.COLUMNS
                    ORDER BY TABLE_NAME, ORDINAL_POSITION;
                    """
                )
                rows = cur.fetchall()
                for row in rows:
                    tbl = row["TABLE_NAME"]
                    col_info = {
                        "name": row["COLUMN_NAME"],
                        "type": row["DATA_TYPE"].lower(),
                        "not_null": "YES" if row["IS_NULLABLE"] == "NO" else "NO",
                        "default": str(row["COLUMN_DEFAULT"]) if row["COLUMN_DEFAULT"] is not None else "",
                        "extra": ""
                    }
                    if tbl not in schema:
                        schema[tbl] = []
                    schema[tbl].append(col_info)
            return schema

        return await anyio.to_thread.run_sync(_get_schema)

    async def get_foreign_keys(self) -> List[Dict[str, str]]:
        """Fetch foreign keys."""
        def _get_fks():
            conn = self._connect()
            foreign_keys = []
            with conn.cursor(as_dict=True) as cur:
                cur.execute(
                    """
                    SELECT 
                        OBJECT_NAME(f.parent_object_id) AS TableName,
                        COL_NAME(fc.parent_object_id, fc.parent_column_id) AS ColumnName,
                        OBJECT_NAME(f.referenced_object_id) AS ReferenceTableName,
                        COL_NAME(fc.referenced_object_id, fc.referenced_column_id) AS ReferenceColumnName
                    FROM 
                        sys.foreign_keys AS f
                    INNER JOIN 
                        sys.foreign_key_columns AS fc ON f.OBJECT_ID = fc.constraint_object_id;
                    """
                )
                rows = cur.fetchall()
                for row in rows:
                    foreign_keys.append({
                        "table_name": row["TableName"],
                        "column_name": row["ColumnName"],
                        "foreign_table_name": row["ReferenceTableName"],
                        "foreign_column_name": row["ReferenceColumnName"]
                    })
            return foreign_keys

        return await anyio.to_thread.run_sync(_get_fks)
