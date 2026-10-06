from __future__ import annotations

import asyncpg
from typing import Dict, List, Any

from .base import BaseConnector

class RedshiftConnector(BaseConnector):
    """
    Asynchronous connector for AWS Redshift using ``asyncpg``.
    Since Redshift is PostgreSQL-compatible, it reuses PostgreSQL query structures
    with Redshift default port 5439.
    """

    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 5439,
        user: str = "",
        password: str = "",
        database: str = "",
    ) -> None:
        super().__init__(host=host, port=port, database=database, user=user, password=password)

    def _make_asyncpg_kwargs(self) -> dict:
        return {
            "host": self.host,
            "port": int(self.port) if self.port else 5439,
            "database": self.database,
            "user": self.user,
            "password": self.password,
        }

    async def test_connection(self) -> bool:
        kwargs = self._make_asyncpg_kwargs()
        try:
            conn = await asyncpg.connect(**kwargs)
            if conn is not None:
                await conn.close()
            return True
        except Exception:
            return False

    async def execute_query(self, query: str) -> List[Dict[str, Any]]:
        kwargs = self._make_asyncpg_kwargs()
        conn = None
        try:
            conn = await asyncpg.connect(**kwargs)
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]
        except Exception as exc:
            raise RuntimeError(f"Redshift query execution failed: {exc}") from exc
        finally:
            if conn is not None:
                await conn.close()

    async def get_schema(self) -> Dict[str, List[Dict[str, str]]]:
        sql = """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position;
        """
        rows = await self.execute_query(sql)

        schema: Dict[str, List[Dict[str, str]]] = {}
        for row in rows:
            table = row["table_name"]
            column_info = {
                "column_name": row["column_name"],
                "data_type": row["data_type"],
            }
            if table not in schema:
                schema[table] = []
            schema[table].append(column_info)

        return schema

    async def get_foreign_keys(self) -> List[Dict[str, str]]:
        # Redshift does not enforce foreign keys but they can be defined in metadata.
        # We query the catalog to retrieve defined foreign key constraints.
        kwargs = self._make_asyncpg_kwargs()
        conn = None
        try:
            conn = await asyncpg.connect(**kwargs)
            query = """
                SELECT
                    tc.table_name           AS table_name,
                    kcu.column_name         AS column_name,
                    ccu.table_name          AS foreign_table_name,
                    ccu.column_name         AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage   AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema      = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                 AND ccu.constraint_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY';
            """
            rows = await conn.fetch(query)
            
            result: List[Dict[str, str]] = [
                {
                    "table_name":          r["table_name"],
                    "column_name":         r["column_name"],
                    "foreign_table_name":  r["foreign_table_name"],
                    "foreign_column_name": r["foreign_column_name"],
                }
                for r in rows
            ]
            return result
        except Exception:
            # Return empty if Redshift catalog schema is different or lacks constraint info
            return []
        finally:
            if conn is not None:
                await conn.close()
