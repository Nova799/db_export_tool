"""Base connector interface for database connections."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseConnector(ABC):
    def __init__(self, host, port, database, username, password):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self._conn = None

    @abstractmethod
    def connect(self) -> None:
        ...

    @abstractmethod
    def test(self) -> tuple:
        """Return (success: bool, message: str)."""
        ...

    @abstractmethod
    def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute a SQL query and return rows as list of dicts."""
        ...

    @abstractmethod
    def close(self) -> None:
        ...

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.close()


def get_connector(db_type, host, port, database, username, password):
    db_type = (db_type or "").lower()
    if db_type == "postgres":
        from .postgres import PostgresConnector
        return PostgresConnector(host, port, database, username, password)
    if db_type == "mysql":
        from .mysql import MySQLConnector
        return MySQLConnector(host, port, database, username, password)
    if db_type in ("mssql", "sqlserver", "sql_server"):
        from .mssql import MSSQLConnector
        return MSSQLConnector(host, port, database, username, password)
    raise ValueError(f"Type de base non supporté : {db_type}")
