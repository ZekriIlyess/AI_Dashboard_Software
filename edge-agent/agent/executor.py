from __future__ import annotations

import logging
from typing import Any, Dict, List

from agent.config import settings

# Load connectors dynamically from nexus_connectors package
from nexus_connectors.postgresql import PostgreSQLConnector
from nexus_connectors.mysql import MySQLConnector
from nexus_connectors.sqlite import SQLiteConnector

logger = logging.getLogger(__name__)

class QueryExecutor:
    """Connects to the local database securely and executes SQL queries."""

    def __init__(self):
        self.db_type = settings.DB_TYPE.lower()
        self.connector = self._build_connector()

    def _build_connector(self):
        """Build appropriate connector from shared nexus_connectors package."""
        if self.db_type in ("postgresql", "postgres"):
            return PostgreSQLConnector(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD
            )
        elif self.db_type == "mysql":
            return MySQLConnector(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD
            )
        elif self.db_type == "sqlite":
            return SQLiteConnector(database_path=settings.DB_HOST)
        else:
            raise ValueError(f"Unsupported database type inside Edge Agent: {self.db_type}")

    async def execute(self, query: str) -> List[Dict[str, Any]]:
        """Run SQL query locally and return row results."""
        logger.info(f"Executing query locally on {self.db_type} database...")
        # Since nexus-connectors execute_query is async, call it
        return await self.connector.execute_query(query)
