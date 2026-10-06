from __future__ import annotations

import typing as _typing
from typing import Any, Dict, List

import aiomysql

from .base import BaseConnector

class MySQLConnector(BaseConnector):
    """
    Asynchronous connector for a MySQL instance using ``aiomysql``.
    """

    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 3306,
        user: str = "",
        password: str = "",
        database: str = "",
        pool_kwargs: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(host=host, port=port, database=database, user=user, password=password)
        self._pool: aiomysql.Pool | None = None
        self._pool_kwargs = pool_kwargs or {}

    async def _get_pool(self) -> aiomysql.Pool:
        if self._pool is not None:
            return self._pool

        cfg = {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "db": self.database,
            "autocommit": True,
        }
        cfg.update(self._pool_kwargs)
        self._pool = await aiomysql.create_pool(**cfg)
        return self._pool

    async def test_connection(self) -> bool:
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    row = await cur.fetchone()
                    return bool(row and row[0] == 1)
        except Exception:
            return False

    async def execute_query(self, query: str) -> List[Dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            cursor = await conn.cursor(aiomysql.DictCursor)
            try:
                await cursor.execute(query)
                rows = await cursor.fetchall()
                return list(rows) if rows else []
            finally:
                await cursor.close()

    async def get_schema(self) -> Dict[str, List[Dict[str, str]]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema=%s AND table_type='BASE TABLE' ORDER BY table_name;",
                    (self.database,)
                )
                tbl_names = [row[0] for row in await cur.fetchall()]

        schema: Dict[str, List[Dict[str, str]]] = {}
        async with pool.acquire() as conn2:
            for tbl_name in sorted(tbl_names):
                async with conn2.cursor() as cur:
                    await cur.execute(f"SHOW COLUMNS FROM {tbl_name};")
                    cols_raw = await cur.fetchall()
                    columns: List[Dict[str, str]] = [
                        {
                            "name": col[0],
                            "type": col[1].lower(),
                            "not_null": "NO" if col[2] == "YES" else "YES",
                            "default": str(col[3]) if col[3] is not None else "",
                            "extra": str(col[4]) + (str(col[5]) if len(col) > 5 else ""),
                        }
                        for col in cols_raw
                    ]
                    schema[tbl_name] = columns

        return schema

    async def get_foreign_keys(self) -> List[Dict[str, str]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT CONSTRAINT_NAME, TABLE_NAME,
                           COLUMN_NAME, REFERENCED_TABLE_NAME,
                           REFERENCED_COLUMN_NAME
                    FROM information_schema.KEY_COLUMN_USAGE
                    WHERE table_schema=%s AND REFERENCED_TABLE_NAME IS NOT NULL
                    ORDER BY CONSTRAINT_NAME;
                    """,
                    (self.database,)
                )
                fk_raw = await cur.fetchall()
                
        foreign_keys: List[Dict[str, str]] = []
        for const_name, tbl, col, ref_tbl, ref_col in fk_raw:
            if ref_tbl is None or ref_col is None:
                continue
            foreign_keys.append(
                {
                    "table_name": tbl,
                    "column_name": col,
                    "foreign_table_name": ref_tbl,
                    "foreign_column_name": ref_col,
                }
            )
        return foreign_keys
