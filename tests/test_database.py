"""
Tests for database layer components.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database.snowflake_client import SnowflakeClient
from database.query_builder import QueryBuilder
from database.models import QueryResult, TableInfo, ColumnInfo

class TestSnowflakeClient:
    """Test cases for SnowflakeClient."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        return {
            'account': 'test_account',
            'user': 'test_user',
            'password': 'test_password',
            'warehouse': 'test_warehouse',
            'database': 'test_database',
            'schema': 'test_schema'
        }
    
    @pytest.fixture
    def client(self, mock_config):
        """Create a SnowflakeClient instance for testing."""
        with patch('database.snowflake_client.get_settings') as mock_settings:
            mock_settings.return_value.get_snowflake_connection_params.return_value = mock_config
            mock_settings.return_value.snowflake.pool_size = 5
            mock_settings.return_value.snowflake.connection_timeout = 30
            mock_settings.return_value.snowflake.query_timeout = 300
            return SnowflakeClient(mock_config)
    
    @patch('database.snowflake_client.snowflake.connector.connect')
    def test_connect_success(self, mock_connect, client):
        """Test successful database connection."""
        mock_connection = Mock()
        mock_connect.return_value = mock_connection
        
        connection = client.connect()
        
        assert connection == mock_connection
        mock_connect.assert_called_once()
    
    @patch('database.snowflake_client.snowflake.connector.connect')
    def test_connect_failure(self, mock_connect, client):
        """Test database connection failure."""
        mock_connect.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception):
            client.connect()
    
    def test_execute_query_success(self, client):
        """Test successful query execution."""
        with patch.object(client, 'get_connection') as mock_get_conn:
            mock_connection = Mock()
            mock_cursor = Mock()
            mock_connection.cursor.return_value = mock_cursor
            mock_get_conn.return_value.__enter__.return_value = mock_connection
            
            # Mock cursor behavior
            mock_cursor.fetchall.return_value = [{'col1': 'value1', 'col2': 'value2'}]
            mock_cursor.description = [('col1',), ('col2',)]
            mock_cursor.sfqid = 'test_query_id'
            
            result = client.execute_query("SELECT * FROM test_table")
            
            assert result.success is True
            assert len(result.data) == 1
            assert result.columns == ['col1', 'col2']
            assert result.metadata['query_id'] == 'test_query_id'
    
    def test_execute_query_failure(self, client):
        """Test query execution failure."""
        with patch.object(client, 'get_connection') as mock_get_conn:
            mock_get_conn.side_effect = Exception("Query failed")
            
            result = client.execute_query("SELECT * FROM test_table")
            
            assert result.success is False
            assert "Query failed" in result.error_message
    
    def test_search_tables_by_keyword(self, client):
        """Test table search functionality."""
        with patch.object(client, 'execute_query') as mock_execute:
            # Mock successful query result
            mock_data = pd.DataFrame([
                {
                    'TABLE_NAME': 'production_data',
                    'SCHEMA_NAME': 'public',
                    'DATABASE_NAME': 'test_db',
                    'TABLE_TYPE': 'BASE TABLE',
                    'ROW_COUNT': 1000,
                    'COMMENT': 'Production data table',
                    'CREATED': '2023-01-01',
                    'LAST_ALTERED': '2023-12-01'
                }
            ])
            
            mock_result = QueryResult(
                data=mock_data,
                columns=list(mock_data.columns),
                row_count=1,
                execution_time=0.5,
                query="test query",
                success=True
            )
            mock_execute.return_value = mock_result
            
            tables = client.search_tables_by_keyword("production")
            
            assert len(tables) == 1
            assert tables[0].name == 'production_data'
            assert tables[0].schema == 'public'
            assert tables[0].row_count == 1000

class TestQueryBuilder:
    """Test cases for QueryBuilder."""
    
    def test_basic_select_query(self):
        """Test basic SELECT query building."""
        builder = QueryBuilder()
        query, params = builder.select("col1", "col2").from_table("test_table").build()
        
        expected_query = "SELECT col1, col2\nFROM test_table"
        assert query == expected_query
        assert params == {}
    
    def test_query_with_where_condition(self):
        """Test query with WHERE condition."""
        builder = QueryBuilder()
        query, params = builder.select("*").from_table("test_table").where("col1 = %(value)s", value="test").build()
        
        assert "WHERE col1 = %(value)s" in query
        assert params["value"] == "test"
    
    def test_query_with_joins(self):
        """Test query with JOIN clauses."""
        builder = QueryBuilder()
        query, params = builder.select("t1.col1", "t2.col2").from_table("table1", "t1").join("table2", "t1.id = t2.table1_id", alias="t2").build()
        
        assert "FROM table1 AS t1" in query
        assert "INNER JOIN table2 AS t2 ON t1.id = t2.table1_id" in query
    
    def test_query_with_order_and_limit(self):
        """Test query with ORDER BY and LIMIT."""
        builder = QueryBuilder()
        query, params = builder.select("*").from_table("test_table").order_by("col1", "DESC").limit(10).build()
        
        assert "ORDER BY col1 DESC" in query
        assert "LIMIT 10" in query
    
    def test_table_search_query(self):
        """Test table search query builder."""
        query, params = QueryBuilder.build_table_search_query("production", limit=25)
        
        assert "information_schema.tables" in query
        assert "ILIKE" in query
        assert params["keyword"] == "%production%"
        assert params["limit"] == 25
    
    def test_trend_analysis_query(self):
        """Test trend analysis query builder."""
        query, params = QueryBuilder.build_trend_analysis_query(
            "sales_data", 
            "date_column", 
            "amount", 
            "6M", 
            "SUM"
        )
        
        assert "DATE_TRUNC('month', date_column)" in query
        assert "SUM(amount)" in query
        assert "6 MONTH" in query

class TestDataModels:
    """Test cases for data models."""
    
    def test_query_result_creation(self):
        """Test QueryResult model creation."""
        data = pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
        result = QueryResult(
            data=data,
            columns=['col1', 'col2'],
            row_count=2,
            execution_time=1.5,
            query="SELECT * FROM test",
            success=True
        )
        
        assert result.success is True
        assert result.row_count == 2
        assert len(result.columns) == 2
        assert result.execution_time == 1.5
    
    def test_query_result_to_dict(self):
        """Test QueryResult to_dict conversion."""
        data = pd.DataFrame({'col1': [1], 'col2': ['a']})
        result = QueryResult(
            data=data,
            columns=['col1', 'col2'],
            row_count=1,
            execution_time=0.5,
            query="SELECT * FROM test",
            success=True
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['success'] is True
        assert result_dict['row_count'] == 1
        assert len(result_dict['data']) == 1
    
    def test_table_info_creation(self):
        """Test TableInfo model creation."""
        table = TableInfo(
            name="test_table",
            schema="public",
            database="test_db",
            table_type="BASE TABLE",
            row_count=1000
        )
        
        assert table.name == "test_table"
        assert table.full_name == "test_db.public.test_table"
        assert table.row_count == 1000
    
    def test_column_info_creation(self):
        """Test ColumnInfo model creation."""
        column = ColumnInfo(
            name="test_column",
            data_type="VARCHAR",
            is_nullable=True,
            comment="Test column"
        )
        
        assert column.name == "test_column"
        assert column.data_type == "VARCHAR"
        assert column.is_nullable is True
        assert column.comment == "Test column"

if __name__ == "__main__":
    pytest.main([__file__])

