"""
Snowflake database client with connection management and query execution.
"""

import time
import logging
from typing import List, Dict, Any, Optional, Union
from contextlib import contextmanager
import pandas as pd
import snowflake.connector
from snowflake.connector import DictCursor
from snowflake.connector.errors import Error as SnowflakeError

from config.settings import get_settings
from .models import QueryResult, TableInfo, ColumnInfo, QueryMetrics

logger = logging.getLogger(__name__)

class SnowflakeClient:
    """
    Snowflake database client with connection pooling and query execution capabilities.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Snowflake client.
        
        Args:
            config: Optional configuration dictionary. If None, uses global settings.
        """
        self.settings = get_settings()
        self.config = config or self.settings.get_snowflake_connection_params()
        self._connection = None
        self._connection_pool = []
        self.max_pool_size = self.settings.snowflake.pool_size
        
    def connect(self) -> snowflake.connector.SnowflakeConnection:
        """
        Establish connection to Snowflake.
        
        Returns:
            Snowflake connection object
            
        Raises:
            SnowflakeError: If connection fails
        """
        try:
            connection = snowflake.connector.connect(
                account=self.config["account"],
                user=self.config["user"],
                password=self.config["password"],
                warehouse=self.config["warehouse"],
                database=self.config["database"],
                schema=self.config["schema"],
                role=self.config.get("role"),
                login_timeout=self.settings.snowflake.connection_timeout,
                network_timeout=self.settings.snowflake.query_timeout
            )
            
            logger.info(f"Successfully connected to Snowflake account: {self.config['account']}")
            return connection
            
        except SnowflakeError as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for getting a database connection.
        
        Yields:
            Snowflake connection object
        """
        connection = None
        try:
            # Try to get connection from pool
            if self._connection_pool:
                connection = self._connection_pool.pop()
                # Test if connection is still valid
                try:
                    connection.cursor().execute("SELECT 1")
                except:
                    connection = None
            
            # Create new connection if needed
            if connection is None:
                connection = self.connect()
            
            yield connection
            
        except Exception as e:
            logger.error(f"Error with database connection: {e}")
            if connection:
                connection.close()
            raise
        finally:
            # Return connection to pool if it's still valid
            if connection and len(self._connection_pool) < self.max_pool_size:
                try:
                    connection.cursor().execute("SELECT 1")
                    self._connection_pool.append(connection)
                except:
                    connection.close()
            elif connection:
                connection.close()
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> QueryResult:
        """
        Execute a SQL query and return results.
        
        Args:
            query: SQL query string
            params: Optional query parameters
            
        Returns:
            QueryResult object containing data and metadata
        """
        start_time = time.time()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(DictCursor)
                
                # Execute query
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                # Fetch results
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                
                # Convert to DataFrame
                df = pd.DataFrame(results, columns=columns) if results else pd.DataFrame()
                
                execution_time = time.time() - start_time
                
                # Get query metrics if available
                query_id = cursor.sfqid if hasattr(cursor, 'sfqid') else None
                
                logger.info(f"Query executed successfully in {execution_time:.2f}s, returned {len(df)} rows")
                
                return QueryResult(
                    data=df,
                    columns=columns,
                    row_count=len(df),
                    execution_time=execution_time,
                    query=query,
                    success=True,
                    metadata={"query_id": query_id}
                )
                
        except SnowflakeError as e:
            execution_time = time.time() - start_time
            logger.error(f"Snowflake query error: {e}")
            
            return QueryResult(
                data=pd.DataFrame(),
                columns=[],
                row_count=0,
                execution_time=execution_time,
                query=query,
                success=False,
                error_message=str(e)
            )
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Unexpected error executing query: {e}")
            
            return QueryResult(
                data=pd.DataFrame(),
                columns=[],
                row_count=0,
                execution_time=execution_time,
                query=query,
                success=False,
                error_message=str(e)
            )
    
    def get_tables(self, schema_pattern: Optional[str] = None, 
                   table_pattern: Optional[str] = None) -> List[TableInfo]:
        """
        Get list of tables in the database.
        
        Args:
            schema_pattern: Optional schema name pattern (SQL LIKE pattern)
            table_pattern: Optional table name pattern (SQL LIKE pattern)
            
        Returns:
            List of TableInfo objects
        """
        query = """
        SELECT 
            table_catalog as database_name,
            table_schema as schema_name,
            table_name,
            table_type,
            row_count,
            comment,
            created,
            last_altered
        FROM information_schema.tables
        WHERE 1=1
        """
        
        params = {}
        
        if schema_pattern:
            query += " AND table_schema ILIKE %(schema_pattern)s"
            params["schema_pattern"] = schema_pattern
            
        if table_pattern:
            query += " AND table_name ILIKE %(table_pattern)s"
            params["table_pattern"] = table_pattern
            
        query += " ORDER BY table_schema, table_name"
        
        result = self.execute_query(query, params)
        
        if not result.success:
            logger.error(f"Failed to get tables: {result.error_message}")
            return []
        
        tables = []
        for row in result.data.to_dict('records'):
            table_info = TableInfo(
                name=row['TABLE_NAME'],
                schema=row['SCHEMA_NAME'],
                database=row['DATABASE_NAME'],
                table_type=row['TABLE_TYPE'],
                row_count=row.get('ROW_COUNT'),
                comment=row.get('COMMENT'),
                created_on=row.get('CREATED'),
                last_altered=row.get('LAST_ALTERED')
            )
            tables.append(table_info)
        
        return tables
    
    def get_table_columns(self, table_name: str, schema_name: Optional[str] = None) -> List[ColumnInfo]:
        """
        Get column information for a specific table.
        
        Args:
            table_name: Name of the table
            schema_name: Optional schema name (uses current schema if not provided)
            
        Returns:
            List of ColumnInfo objects
        """
        query = """
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default,
            comment
        FROM information_schema.columns
        WHERE table_name = %(table_name)s
        """
        
        params = {"table_name": table_name.upper()}
        
        if schema_name:
            query += " AND table_schema = %(schema_name)s"
            params["schema_name"] = schema_name.upper()
        
        query += " ORDER BY ordinal_position"
        
        result = self.execute_query(query, params)
        
        if not result.success:
            logger.error(f"Failed to get columns for table {table_name}: {result.error_message}")
            return []
        
        columns = []
        for row in result.data.to_dict('records'):
            column_info = ColumnInfo(
                name=row['COLUMN_NAME'],
                data_type=row['DATA_TYPE'],
                is_nullable=row['IS_NULLABLE'] == 'YES',
                default_value=row.get('COLUMN_DEFAULT'),
                comment=row.get('COMMENT')
            )
            columns.append(column_info)
        
        return columns
    
    def search_tables_by_keyword(self, keyword: str, limit: int = 50) -> List[TableInfo]:
        """
        Search for tables containing a specific keyword in name or comment.
        
        Args:
            keyword: Keyword to search for
            limit: Maximum number of results to return
            
        Returns:
            List of TableInfo objects matching the keyword
        """
        query = """
        SELECT 
            table_catalog as database_name,
            table_schema as schema_name,
            table_name,
            table_type,
            row_count,
            comment,
            created,
            last_altered
        FROM information_schema.tables
        WHERE (
            table_name ILIKE %(keyword)s 
            OR comment ILIKE %(keyword)s
        )
        ORDER BY 
            CASE WHEN table_name ILIKE %(exact_keyword)s THEN 1 ELSE 2 END,
            table_name
        LIMIT %(limit)s
        """
        
        params = {
            "keyword": f"%{keyword}%",
            "exact_keyword": keyword,
            "limit": limit
        }
        
        result = self.execute_query(query, params)
        
        if not result.success:
            logger.error(f"Failed to search tables: {result.error_message}")
            return []
        
        tables = []
        for row in result.data.to_dict('records'):
            table_info = TableInfo(
                name=row['TABLE_NAME'],
                schema=row['SCHEMA_NAME'],
                database=row['DATABASE_NAME'],
                table_type=row['TABLE_TYPE'],
                row_count=row.get('ROW_COUNT'),
                comment=row.get('COMMENT'),
                created_on=row.get('CREATED'),
                last_altered=row.get('LAST_ALTERED')
            )
            tables.append(table_info)
        
        return tables
    
    def test_connection(self) -> bool:
        """
        Test the database connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            result = self.execute_query("SELECT CURRENT_VERSION()")
            return result.success
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def close_all_connections(self):
        """Close all connections in the pool."""
        for conn in self._connection_pool:
            try:
                conn.close()
            except:
                pass
        self._connection_pool.clear()
        
        if self._connection:
            try:
                self._connection.close()
            except:
                pass
            self._connection = None
    
    def __del__(self):
        """Cleanup connections when object is destroyed."""
        self.close_all_connections()

