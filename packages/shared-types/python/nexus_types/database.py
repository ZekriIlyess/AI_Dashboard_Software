from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class DatabaseType(str, Enum):
    postgresql = "postgresql"
    mysql = "mysql"
    sqlite = "sqlite"
    sqlserver = "sqlserver"
    snowflake = "snowflake"
    bigquery = "bigquery"
    redshift = "redshift"


class ConnectionConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    db_type: DatabaseType
    host: str
    port: int
    database: str
    username: str
    password: Optional[str] = None
    ssl: bool = False
    is_active: bool = True


class ColumnStats(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    mean: Optional[float] = None
    median: Optional[float] = None
    std_dev: Optional[float] = None
    null_count: int = 0
    distinct_count: int = 0


class ColumnInfo(BaseModel):
    name: str
    data_type: str
    is_nullable: bool
    is_primary_key: bool = False
    is_foreign_key: bool = False
    default_value: Optional[str] = None
    sample_values: Optional[List[str]] = None
    stats: Optional[ColumnStats] = None


class ForeignKeyInfo(BaseModel):
    column: str
    referenced_table: str
    referenced_column: str


class IndexInfo(BaseModel):
    name: str
    columns: List[str]
    is_unique: bool


class TableInfo(BaseModel):
    name: str
    schema_name: str = "public"
    columns: List[ColumnInfo]
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None
    primary_key: Optional[List[str]] = None
    foreign_keys: List[ForeignKeyInfo] = []
    indexes: List[IndexInfo] = []


class SchemaInfo(BaseModel):
    tables: List[TableInfo]
    total_tables: int = 0
    total_columns: int = 0
    extracted_at: str
