"""
Data models for database operations.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import pandas as pd

@dataclass
class ColumnInfo:
    """Information about a database column."""
    name: str
    data_type: str
    is_nullable: bool
    default_value: Optional[str] = None
    comment: Optional[str] = None

@dataclass
class TableInfo:
    """Information about a database table."""
    name: str
    schema: str
    database: str
    table_type: str
    row_count: Optional[int] = None
    columns: List[ColumnInfo] = None
    comment: Optional[str] = None
    created_on: Optional[datetime] = None
    last_altered: Optional[datetime] = None
    
    def __post_init__(self):
        if self.columns is None:
            self.columns = []
    
    @property
    def full_name(self) -> str:
        """Get the fully qualified table name."""
        return f"{self.database}.{self.schema}.{self.name}"

@dataclass
class QueryResult:
    """Result of a database query execution."""
    data: pd.DataFrame
    columns: List[str]
    row_count: int
    execution_time: float
    query: str
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        
        # Ensure consistency between data and columns
        if not self.data.empty:
            self.columns = list(self.data.columns)
            self.row_count = len(self.data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format."""
        return {
            "data": self.data.to_dict("records") if not self.data.empty else [],
            "columns": self.columns,
            "row_count": self.row_count,
            "execution_time": self.execution_time,
            "query": self.query,
            "success": self.success,
            "error_message": self.error_message,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """Convert result to JSON string."""
        import json
        result_dict = self.to_dict()
        # Convert DataFrame to JSON-serializable format
        if not self.data.empty:
            result_dict["data"] = self.data.to_json(orient="records", date_format="iso")
        return json.dumps(result_dict, indent=2)

@dataclass
class QueryMetrics:
    """Metrics for query performance analysis."""
    query_id: str
    execution_time: float
    rows_scanned: Optional[int] = None
    rows_returned: int = 0
    bytes_scanned: Optional[int] = None
    warehouse_size: Optional[str] = None
    compilation_time: Optional[float] = None
    queued_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "query_id": self.query_id,
            "execution_time": self.execution_time,
            "rows_scanned": self.rows_scanned,
            "rows_returned": self.rows_returned,
            "bytes_scanned": self.bytes_scanned,
            "warehouse_size": self.warehouse_size,
            "compilation_time": self.compilation_time,
            "queued_time": self.queued_time
        }

