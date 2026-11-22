"""Data models (dataclasses) for the DB Export Tool."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class ConnectionConfig:
    id: Optional[int] = None
    name: str = ""
    db_type: str = "postgres"  # postgres | mysql | mssql
    host: str = ""
    port: Optional[int] = None
    database: str = ""
    username: str = ""
    password: str = ""
    created_at: Optional[str] = None
    last_test: Optional[str] = None

    @property
    def default_port(self) -> int:
        return {"postgres": 5432, "mysql": 3306, "mssql": 1433}.get(self.db_type, 5432)


@dataclass
class SharePointFolder:
    id: Optional[int] = None
    name: str = ""
    site_url: str = ""
    drive_id: Optional[str] = None
    folder_path: str = "/"
    auth_mode: str = "app"  # app | oauth
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: str = ""
    created_at: Optional[str] = None
    last_test: Optional[str] = None


@dataclass
class Recovery:
    id: Optional[int] = None
    name: str = ""
    connection_id: Optional[int] = None
    connection_name: Optional[str] = None
    script_path: str = ""
    sharepoint_folder_id: Optional[int] = None
    sharepoint_folder_name: Optional[str] = None
    sharepoint_path: Optional[str] = None
    frequency: str = "manual"  # manual | weekly | monthly | quarterly
    last_execution: Optional[str] = None
    next_execution: Optional[str] = None
    status: str = "pending"


@dataclass
class Execution:
    id: Optional[int] = None
    recovery_id: Optional[int] = None
    date_execution: Optional[str] = None
    lignes_exportees: int = 0
    statut: str = ""
    duree_ms: int = 0
    csv_filename: Optional[str] = None
