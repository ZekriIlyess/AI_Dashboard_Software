from __future__ import annotations

import typing as _typing
from typing import Any, Dict, List

import aiosqlite

from .base import BaseConnector

class SQLiteConnector(BaseConnector):
    """
    Asynchronous connector for an SQLite database file.
    """

    def __init__(self, database_path: str) -> None:
        # For SQLite, the path replaces the standard host/port.
        super().__init__(host=database_path, port=0, database="", user="", password="")
        self.path = database_path

    async def test_connection(self) -> bool:
        try:
            conn = await aiosqlite.connect(self.path)
            await conn.close()
            return True
        except Exception:
            return False

    async def execute_query(self, query: str) -> List[_typing.Dict[str, _typing.Any]]:
        conn = await aiosqlite.connect(self.path)
        try:
            cursor = await conn.cursor()
            await cursor.execute(query)
            rows = await cursor.fetchall()
            col_names = [desc[0] for desc in cursor.description]
            return [{col_name: value for col_name, value in zip(col_names, row)} for row in rows]
        finally:
            await conn.commit()
            await conn.close()

    async def _list_of_rows(self, sql: str) -> List[List[str]]:
        conn = await aiosqlite.connect(self.path)
        try:
            cur = await conn.cursor()
            await cur.execute(sql)
            rows = [list(row) for row in (await cur.fetchall())]
            return rows
        finally:
            await cur.close()
            await conn.commit()
            await conn.close()

    async def get_schema(self) -> _typing.Dict[str, List[_typing.Dict[str, str]]]:
        tbls = await self._list_of_rows(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        )
        table_names: List[str] = [row[0] for row in tbls]

        schema: _typing.Dict[str, List[_typing.Dict[str, str]]] = {}
        for tbl_name in sorted(table_names):
            cols_raw = await self._list_of_rows(f"PRAGMA table_info({_typing.cast(str, tbl_name)});")
            columns: List[_typing.Dict[str, str]] = []
            for _cid, col_name, typ, not_null, default_val, pk in cols_raw:
                columns.append(
                    {
                        "name": _typing.cast(str, col_name),
                        "type": _typing.cast(str, typ).lower(),
                        "not_null": _typing.cast(str, not_null),
                        "primary_key": _typing.cast(str, pk),
                        "default_value": _typing.cast(str, default_val) if default_val is not None else "",
                    }
                )
            schema[tbl_name] = columns
        return schema

    async def get_foreign_keys(self) -> List[_typing.Dict[str, str]]:
        fk_dicts: List[_typing.Dict[str, str]] = []
        tbls = await self._list_of_rows("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        for tbl_row in tbls:
            tbl_name = tbl_row[0]
            raw = await self._list_of_rows(f"PRAGMA foreign_key_list({tbl_name});")
            for _id, dest_tbl, dest_col, src_col, upd_action, del_action in raw:
                fk_dicts.append(
                    {
                        "table_name": tbl_name,
                        "column_name": _typing.cast(str, src_col),
                        "foreign_table_name": _typing.cast(str, dest_tbl),
                        "foreign_column_name": _typing.cast(str, dest_col),
                    }
                )
        return fk_dicts
