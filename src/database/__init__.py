"""
Database abstraction layer for Snowflake integration.

This module provides a clean interface for interacting with Snowflake databases,
including connection management, query execution, and result processing.
"""

from .snowflake_client import SnowflakeClient
from .query_builder import QueryBuilder
from .models import QueryResult, TableInfo, ColumnInfo

__all__ = [
    "SnowflakeClient",
    "QueryBuilder", 
    "QueryResult",
    "TableInfo",
    "ColumnInfo",
]

