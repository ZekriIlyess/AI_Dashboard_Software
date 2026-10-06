from __future__ import annotations

import abc
from typing import Any, Dict, List

class BaseConnector(abc.ABC):
    """
    Abstract base class for all database connectors.
    """

    def __init__(self, **kwargs: Any) -> None:
        self.host = kwargs.get("host")
        self.port: int | None = kwargs.get("port") or 5432
        self.database = kwargs.get("database")
        self.user = kwargs.get("user")
        self.password = kwargs.get("password")

    @abc.abstractmethod
    async def test_connection(self) -> None:
        """
        Attempt a connection to the target database and close it.
        Must raise an exception if the connection cannot be established.
        """

    @abc.abstractmethod
    async def get_schema(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Return a dictionary describing the current schema.
        """

    @abc.abstractmethod
    async def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute the supplied query string and return its rows.
        """
