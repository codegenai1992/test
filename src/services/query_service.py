"""
Query service for handling database queries and AI interactions.
"""

import logging
from typing import Dict, List, Any, Optional
import time

from config.settings import get_settings
from ..database.snowflake_client import SnowflakeClient
from ..ai.cortex_client import CortexAIClient
from ..processing.query_processor import QueryProcessor, ProcessedQuery

logger = logging.getLogger(__name__)

class QueryService:
    """
    Service for handling database queries and AI interactions.
    """
    
    def __init__(self):
        """Initialize the query service."""
        self.settings = get_settings()
        
        # Initialize core components
        self.snowflake_client = SnowflakeClient()
        self.cortex_client = CortexAIClient(self.snowflake_client)
        self.query_processor = QueryProcessor()
        
        logger.info("Query service initialized")
    
    def execute_database_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a database query.
        
        Args:
            query: SQL query string
            params: Optional query parameters
            
        Returns:
            Query result dictionary
        """
        try:
            result = self.snowflake_client.execute_query(query, params)
            
            return {
                'success': result.success,
                'data': result.data,
                'columns': result.columns,
                'row_count': result.row_count,
                'execution_time': result.execution_time,
                'error_message': result.error_message,
                'metadata': result.metadata
            }
            
        except Exception as e:
            logger.error(f"Database query execution failed: {e}")
            return {
                'success': False,
                'data': None,
                'columns': [],
                'row_count': 0,
                'execution_time': 0,
                'error_message': str(e),
                'metadata': {}
            }
    
    def get_table_information(self, table_pattern: Optional[str] = None, 
                            schema_pattern: Optional[str] = None) -> Dict[str, Any]:
        """
        Get table information from the database.
        
        Args:
            table_pattern: Optional table name pattern
            schema_pattern: Optional schema name pattern
            
        Returns:
            Table information dictionary
        """
        try:
            tables = self.snowflake_client.get_tables(schema_pattern, table_pattern)
            
            table_info = []
            for table in tables:
                # Get column information for each table
                columns = self.snowflake_client.get_table_columns(table.name, table.schema)
                
                table_data = {
                    'name': table.name,
                    'schema': table.schema,
                    'database': table.database,
                    'full_name': table.full_name,
                    'type': table.table_type,
                    'row_count': table.row_count,
                    'comment': table.comment,
                    'created_on': table.created_on.isoformat() if table.created_on else None,
                    'last_altered': table.last_altered.isoformat() if table.last_altered else None,
                    'columns': [
                        {
                            'name': col.name,
                            'data_type': col.data_type,
                            'is_nullable': col.is_nullable,
                            'default_value': col.default_value,
                            'comment': col.comment
                        }
                        for col in columns
                    ]
                }
                table_info.append(table_data)
            
            return {
                'success': True,
                'tables': table_info,
                'count': len(table_info),
                'error_message': None
            }
            
        except Exception as e:
            logger.error(f"Failed to get table information: {e}")
            return {
                'success': False,
                'tables': [],
                'count': 0,
                'error_message': str(e)
            }
    
    def search_tables_by_keywords(self, keywords: List[str], limit: int = 50) -> Dict[str, Any]:
        """
        Search for tables using keywords.
        
        Args:
            keywords: List of search keywords
            limit: Maximum number of results
            
        Returns:
            Search results dictionary
        """
        try:
            all_tables = []
            
            # Search for each keyword
            for keyword in keywords:
                tables = self.snowflake_client.search_tables_by_keyword(keyword, limit)
                all_tables.extend(tables)
            
            # Remove duplicates and format results
            seen_tables = set()
            unique_tables = []
            
            for table in all_tables:
                table_key = f"{table.database}.{table.schema}.{table.name}"
                if table_key not in seen_tables:
                    seen_tables.add(table_key)
                    unique_tables.append({
                        'name': table.name,
                        'schema': table.schema,
                        'database': table.database,
                        'full_name': table.full_name,
                        'type': table.table_type,
                        'row_count': table.row_count,
                        'comment': table.comment,
                        'created_on': table.created_on.isoformat() if table.created_on else None,
                        'last_altered': table.last_altered.isoformat() if table.last_altered else None
                    })
            
            return {
                'success': True,
                'tables': unique_tables[:limit],
                'search_terms': keywords,
                'total_found': len(unique_tables),
                'error_message': None
            }
            
        except Exception as e:
            logger.error(f"Table search failed: {e}")
            return {
                'success': False,
                'tables': [],
                'search_terms': keywords,
                'total_found': 0,
                'error_message': str(e)
            }
    
    def generate_ai_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate AI response using Cortex AI.
        
        Args:
            prompt: Input prompt
            context: Optional context information
            
        Returns:
            AI response dictionary
        """
        try:
            response = self.cortex_client.complete(prompt)
            
            return {
                'success': response['success'],
                'response': response.get('response'),
                'model': response.get('model'),
                'execution_time': response.get('execution_time'),
                'error_message': response.get('error'),
                'metadata': response.get('metadata', {})
            }
            
        except Exception as e:
            logger.error(f"AI response generation failed: {e}")
            return {
                'success': False,
                'response': None,
                'model': None,
                'execution_time': 0,
                'error_message': str(e),
                'metadata': {}
            }
    
    def analyze_query_intent(self, query: str) -> ProcessedQuery:
        """
        Analyze user query to determine intent and extract keywords.
        
        Args:
            query: User query string
            
        Returns:
            ProcessedQuery object
        """
        try:
            return self.query_processor.process_user_query(query)
        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            # Return a basic processed query with error information
            from ..processing.keyword_extractor import ExtractedKeywords
            
            keywords = ExtractedKeywords(
                primary_keywords=[],
                secondary_keywords=[],
                entities=[],
                intent='general_query',
                confidence=0.0,
                original_query=query
            )
            
            return ProcessedQuery(
                original_query=query,
                keywords=keywords,
                intent='general_query',
                suggested_tables=[],
                query_parameters={},
                confidence=0.0,
                processing_metadata={'error': str(e)}
            )
    
    def get_sample_data(self, table_name: str, schema_name: Optional[str] = None, 
                       limit: int = 10) -> Dict[str, Any]:
        """
        Get sample data from a table.
        
        Args:
            table_name: Name of the table
            schema_name: Optional schema name
            limit: Number of rows to sample
            
        Returns:
            Sample data dictionary
        """
        try:
            # Build the query
            full_table_name = f"{schema_name}.{table_name}" if schema_name else table_name
            query = f"SELECT * FROM {full_table_name} LIMIT {limit}"
            
            result = self.snowflake_client.execute_query(query)
            
            if result.success:
                return {
                    'success': True,
                    'data': result.data.to_dict('records') if not result.data.empty else [],
                    'columns': result.columns,
                    'row_count': result.row_count,
                    'table_name': table_name,
                    'schema_name': schema_name,
                    'error_message': None
                }
            else:
                return {
                    'success': False,
                    'data': [],
                    'columns': [],
                    'row_count': 0,
                    'table_name': table_name,
                    'schema_name': schema_name,
                    'error_message': result.error_message
                }
                
        except Exception as e:
            logger.error(f"Failed to get sample data: {e}")
            return {
                'success': False,
                'data': [],
                'columns': [],
                'row_count': 0,
                'table_name': table_name,
                'schema_name': schema_name,
                'error_message': str(e)
            }
    
    def test_connections(self) -> Dict[str, Any]:
        """
        Test all service connections.
        
        Returns:
            Connection status dictionary
        """
        status = {
            'snowflake': False,
            'cortex_ai': False,
            'overall': False,
            'errors': []
        }
        
        # Test Snowflake connection
        try:
            status['snowflake'] = self.snowflake_client.test_connection()
            if not status['snowflake']:
                status['errors'].append("Snowflake connection failed")
        except Exception as e:
            logger.error(f"Snowflake connection test error: {e}")
            status['errors'].append(f"Snowflake error: {str(e)}")
        
        # Test Cortex AI connection
        try:
            status['cortex_ai'] = self.cortex_client.test_connection()
            if not status['cortex_ai']:
                status['errors'].append("Cortex AI connection failed")
        except Exception as e:
            logger.error(f"Cortex AI connection test error: {e}")
            status['errors'].append(f"Cortex AI error: {str(e)}")
        
        # Overall status
        status['overall'] = status['snowflake'] and status['cortex_ai']
        
        return status
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get comprehensive service status information.
        
        Returns:
            Service status dictionary
        """
        return {
            'service_name': 'QueryService',
            'initialized': True,
            'connections': self.test_connections(),
            'settings': {
                'snowflake_timeout': self.settings.snowflake.query_timeout,
                'cortex_model': self.settings.cortex_ai.model,
                'max_retries': self.settings.snowflake.max_retries
            },
            'capabilities': [
                'database_queries',
                'table_discovery',
                'ai_responses',
                'query_analysis',
                'sample_data_retrieval'
            ]
        }

