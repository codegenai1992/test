"""
SQL query builder for dynamic query construction.
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date
import re

class QueryBuilder:
    """
    Dynamic SQL query builder for Snowflake with support for various query patterns.
    """
    
    def __init__(self):
        """Initialize the query builder."""
        self.reset()
    
    def reset(self):
        """Reset the query builder to initial state."""
        self._select_fields = []
        self._from_table = None
        self._joins = []
        self._where_conditions = []
        self._group_by = []
        self._having_conditions = []
        self._order_by = []
        self._limit = None
        self._parameters = {}
    
    def select(self, *fields: str) -> 'QueryBuilder':
        """
        Add SELECT fields to the query.
        
        Args:
            *fields: Field names or expressions to select
            
        Returns:
            Self for method chaining
        """
        self._select_fields.extend(fields)
        return self
    
    def from_table(self, table: str, alias: Optional[str] = None) -> 'QueryBuilder':
        """
        Set the FROM table.
        
        Args:
            table: Table name (can be fully qualified)
            alias: Optional table alias
            
        Returns:
            Self for method chaining
        """
        if alias:
            self._from_table = f"{table} AS {alias}"
        else:
            self._from_table = table
        return self
    
    def join(self, table: str, condition: str, join_type: str = "INNER", 
             alias: Optional[str] = None) -> 'QueryBuilder':
        """
        Add a JOIN clause.
        
        Args:
            table: Table to join
            condition: JOIN condition
            join_type: Type of join (INNER, LEFT, RIGHT, FULL)
            alias: Optional table alias
            
        Returns:
            Self for method chaining
        """
        table_expr = f"{table} AS {alias}" if alias else table
        join_clause = f"{join_type} JOIN {table_expr} ON {condition}"
        self._joins.append(join_clause)
        return self
    
    def where(self, condition: str, **params) -> 'QueryBuilder':
        """
        Add WHERE condition.
        
        Args:
            condition: WHERE condition with parameter placeholders
            **params: Parameters for the condition
            
        Returns:
            Self for method chaining
        """
        self._where_conditions.append(condition)
        self._parameters.update(params)
        return self
    
    def where_in(self, field: str, values: List[Any]) -> 'QueryBuilder':
        """
        Add WHERE IN condition.
        
        Args:
            field: Field name
            values: List of values for IN clause
            
        Returns:
            Self for method chaining
        """
        if not values:
            return self
        
        param_name = f"{field.replace('.', '_')}_in_values"
        placeholders = ', '.join([f"%(param_{i})s" for i in range(len(values))])
        condition = f"{field} IN ({placeholders})"
        
        self._where_conditions.append(condition)
        for i, value in enumerate(values):
            self._parameters[f"param_{i}"] = value
        
        return self
    
    def where_like(self, field: str, pattern: str, case_sensitive: bool = False) -> 'QueryBuilder':
        """
        Add WHERE LIKE condition.
        
        Args:
            field: Field name
            pattern: LIKE pattern
            case_sensitive: Whether to use case-sensitive matching
            
        Returns:
            Self for method chaining
        """
        operator = "LIKE" if case_sensitive else "ILIKE"
        param_name = f"{field.replace('.', '_')}_like"
        condition = f"{field} {operator} %({param_name})s"
        
        self._where_conditions.append(condition)
        self._parameters[param_name] = pattern
        return self
    
    def where_date_range(self, field: str, start_date: Optional[Union[date, datetime]] = None,
                        end_date: Optional[Union[date, datetime]] = None) -> 'QueryBuilder':
        """
        Add date range WHERE condition.
        
        Args:
            field: Date field name
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            Self for method chaining
        """
        if start_date:
            param_name = f"{field.replace('.', '_')}_start"
            self._where_conditions.append(f"{field} >= %({param_name})s")
            self._parameters[param_name] = start_date
        
        if end_date:
            param_name = f"{field.replace('.', '_')}_end"
            self._where_conditions.append(f"{field} <= %({param_name})s")
            self._parameters[param_name] = end_date
        
        return self
    
    def group_by(self, *fields: str) -> 'QueryBuilder':
        """
        Add GROUP BY fields.
        
        Args:
            *fields: Field names to group by
            
        Returns:
            Self for method chaining
        """
        self._group_by.extend(fields)
        return self
    
    def having(self, condition: str, **params) -> 'QueryBuilder':
        """
        Add HAVING condition.
        
        Args:
            condition: HAVING condition
            **params: Parameters for the condition
            
        Returns:
            Self for method chaining
        """
        self._having_conditions.append(condition)
        self._parameters.update(params)
        return self
    
    def order_by(self, field: str, direction: str = "ASC") -> 'QueryBuilder':
        """
        Add ORDER BY clause.
        
        Args:
            field: Field name to order by
            direction: Sort direction (ASC or DESC)
            
        Returns:
            Self for method chaining
        """
        self._order_by.append(f"{field} {direction.upper()}")
        return self
    
    def limit(self, count: int) -> 'QueryBuilder':
        """
        Add LIMIT clause.
        
        Args:
            count: Maximum number of rows to return
            
        Returns:
            Self for method chaining
        """
        self._limit = count
        return self
    
    def build(self) -> tuple[str, Dict[str, Any]]:
        """
        Build the final SQL query and parameters.
        
        Returns:
            Tuple of (query_string, parameters_dict)
        """
        if not self._select_fields:
            raise ValueError("SELECT fields are required")
        
        if not self._from_table:
            raise ValueError("FROM table is required")
        
        # Build SELECT clause
        select_clause = "SELECT " + ", ".join(self._select_fields)
        
        # Build FROM clause
        from_clause = f"FROM {self._from_table}"
        
        # Build query parts
        query_parts = [select_clause, from_clause]
        
        # Add JOINs
        if self._joins:
            query_parts.extend(self._joins)
        
        # Add WHERE clause
        if self._where_conditions:
            where_clause = "WHERE " + " AND ".join(self._where_conditions)
            query_parts.append(where_clause)
        
        # Add GROUP BY
        if self._group_by:
            group_clause = "GROUP BY " + ", ".join(self._group_by)
            query_parts.append(group_clause)
        
        # Add HAVING
        if self._having_conditions:
            having_clause = "HAVING " + " AND ".join(self._having_conditions)
            query_parts.append(having_clause)
        
        # Add ORDER BY
        if self._order_by:
            order_clause = "ORDER BY " + ", ".join(self._order_by)
            query_parts.append(order_clause)
        
        # Add LIMIT
        if self._limit:
            limit_clause = f"LIMIT {self._limit}"
            query_parts.append(limit_clause)
        
        query = "\n".join(query_parts)
        return query, self._parameters.copy()
    
    @staticmethod
    def build_table_search_query(keyword: str, limit: int = 50) -> tuple[str, Dict[str, Any]]:
        """
        Build a query to search for tables by keyword.
        
        Args:
            keyword: Keyword to search for
            limit: Maximum number of results
            
        Returns:
            Tuple of (query_string, parameters_dict)
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
        
        return query, params
    
    @staticmethod
    def build_trend_analysis_query(table_name: str, date_column: str, 
                                 value_column: str, period: str = "1Y",
                                 aggregation: str = "SUM") -> tuple[str, Dict[str, Any]]:
        """
        Build a query for trend analysis.
        
        Args:
            table_name: Name of the table to analyze
            date_column: Name of the date column
            value_column: Name of the value column to aggregate
            period: Time period (1M, 3M, 6M, 1Y, 2Y)
            aggregation: Aggregation function (SUM, AVG, COUNT, etc.)
            
        Returns:
            Tuple of (query_string, parameters_dict)
        """
        # Convert period to SQL interval
        period_map = {
            "1M": "1 MONTH",
            "3M": "3 MONTH", 
            "6M": "6 MONTH",
            "1Y": "1 YEAR",
            "2Y": "2 YEAR"
        }
        
        interval = period_map.get(period, "1 YEAR")
        
        query = f"""
        SELECT 
            DATE_TRUNC('month', {date_column}) as period,
            {aggregation}({value_column}) as value,
            COUNT(*) as record_count
        FROM {table_name}
        WHERE {date_column} >= DATEADD({interval.split()[1]}, -{interval.split()[0]}, CURRENT_DATE())
        GROUP BY DATE_TRUNC('month', {date_column})
        ORDER BY period
        """
        
        return query, {}
    
    @staticmethod
    def sanitize_identifier(identifier: str) -> str:
        """
        Sanitize SQL identifier to prevent injection.
        
        Args:
            identifier: SQL identifier (table name, column name, etc.)
            
        Returns:
            Sanitized identifier
        """
        # Remove any characters that aren't alphanumeric, underscore, or dot
        sanitized = re.sub(r'[^a-zA-Z0-9_.]', '', identifier)
        
        # Ensure it doesn't start with a number
        if sanitized and sanitized[0].isdigit():
            sanitized = f"_{sanitized}"
        
        return sanitized
    
    @staticmethod
    def escape_string_literal(value: str) -> str:
        """
        Escape string literal for SQL.
        
        Args:
            value: String value to escape
            
        Returns:
            Escaped string literal
        """
        # Replace single quotes with double single quotes
        return value.replace("'", "''")

# Convenience functions for common query patterns

def build_table_discovery_query(keywords: List[str], limit: int = 50) -> tuple[str, Dict[str, Any]]:
    """
    Build a query to discover tables based on multiple keywords.
    
    Args:
        keywords: List of keywords to search for
        limit: Maximum number of results
        
    Returns:
        Tuple of (query_string, parameters_dict)
    """
    if not keywords:
        return QueryBuilder.build_table_search_query("", limit)
    
    # Build conditions for each keyword
    conditions = []
    params = {"limit": limit}
    
    for i, keyword in enumerate(keywords):
        param_key = f"keyword_{i}"
        conditions.append(f"(table_name ILIKE %({param_key})s OR comment ILIKE %({param_key})s)")
        params[param_key] = f"%{keyword}%"
    
    where_clause = " OR ".join(conditions)
    
    query = f"""
    SELECT 
        table_catalog as database_name,
        table_schema as schema_name,
        table_name,
        table_type,
        row_count,
        comment,
        created,
        last_altered,
        -- Calculate relevance score
        (
            CASE WHEN table_name ILIKE %({list(params.keys())[0]})s THEN 10 ELSE 0 END +
            CASE WHEN comment ILIKE %({list(params.keys())[0]})s THEN 5 ELSE 0 END
        ) as relevance_score
    FROM information_schema.tables
    WHERE {where_clause}
    ORDER BY relevance_score DESC, table_name
    LIMIT %(limit)s
    """
    
    return query, params

