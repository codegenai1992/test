"""
Table discovery agent for finding relevant database tables.
"""

import time
import logging
from typing import List, Dict, Any

from .base_agent import BaseAgent, AgentResult
from ..processing.query_processor import ProcessedQuery
from ..database.models import TableInfo

logger = logging.getLogger(__name__)

class TableDiscoveryAgent(BaseAgent):
    """
    Agent specialized in discovering and analyzing database tables based on user queries.
    """
    
    def __init__(self):
        """Initialize the table discovery agent."""
        super().__init__(
            name="Table Discovery Agent",
            description="Discovers and analyzes database tables based on keywords and user intent"
        )
    
    def can_handle(self, processed_query: ProcessedQuery) -> bool:
        """
        Determine if this agent can handle the query.
        
        Args:
            processed_query: ProcessedQuery object
            
        Returns:
            True if this agent can handle the query
        """
        # Handle table discovery intents
        if processed_query.intent == 'table_discovery':
            return True
        
        # Also handle queries with table-related keywords
        table_keywords = {'table', 'tables', 'list', 'show', 'find', 'search', 'related'}
        query_words = set(processed_query.original_query.lower().split())
        
        return bool(table_keywords.intersection(query_words))
    
    def execute(self, processed_query: ProcessedQuery) -> AgentResult:
        """
        Execute table discovery based on the processed query.
        
        Args:
            processed_query: ProcessedQuery object
            
        Returns:
            AgentResult with discovered tables and analysis
        """
        start_time = time.time()
        
        try:
            # Validate the query
            if not self.validate_query(processed_query):
                return AgentResult(
                    success=False,
                    data=None,
                    message="Invalid query for table discovery",
                    suggestions=["Please provide keywords to search for tables"],
                    metadata={},
                    execution_time=time.time() - start_time,
                    agent_name=self.name
                )
            
            # Extract search terms from keywords
            search_terms = processed_query.keywords.primary_keywords + processed_query.keywords.entities
            
            if not search_terms:
                # If no specific keywords, show all tables (limited)
                tables = self._get_all_tables()
                message = "Here are the available tables in the database:"
            else:
                # Search for tables based on keywords
                tables = self._search_tables_by_keywords(search_terms)
                message = f"Found {len(tables)} tables related to your search:"
            
            # Analyze tables with AI
            ai_analysis = self._analyze_tables_with_ai(processed_query, tables)
            
            # Generate suggestions
            suggestions = self._generate_suggestions(processed_query, tables)
            
            # Prepare result data
            result_data = {
                'tables': [self._format_table_info(table) for table in tables],
                'search_terms': search_terms,
                'total_count': len(tables),
                'ai_analysis': ai_analysis
            }
            
            execution_time = time.time() - start_time
            
            return AgentResult(
                success=True,
                data=result_data,
                message=message,
                suggestions=suggestions,
                metadata={
                    'search_terms': search_terms,
                    'table_count': len(tables),
                    'ai_analysis_success': ai_analysis.get('success', False)
                },
                execution_time=execution_time,
                agent_name=self.name
            )
            
        except Exception as e:
            return self.handle_error(e, processed_query)
    
    def _get_all_tables(self) -> List[TableInfo]:
        """Get all available tables (limited)."""
        try:
            return self.snowflake_client.get_tables()[:self.max_results]
        except Exception as e:
            logger.error(f"Error getting all tables: {e}")
            return []
    
    def _search_tables_by_keywords(self, keywords: List[str]) -> List[TableInfo]:
        """
        Search for tables using keywords.
        
        Args:
            keywords: List of search keywords
            
        Returns:
            List of matching TableInfo objects
        """
        all_tables = []
        
        try:
            # Search for each keyword and combine results
            for keyword in keywords:
                tables = self.snowflake_client.search_tables_by_keyword(
                    keyword, 
                    limit=self.max_results
                )
                all_tables.extend(tables)
            
            # Remove duplicates while preserving order
            seen_tables = set()
            unique_tables = []
            
            for table in all_tables:
                table_key = f"{table.database}.{table.schema}.{table.name}"
                if table_key not in seen_tables:
                    seen_tables.add(table_key)
                    unique_tables.append(table)
            
            # Sort by relevance (tables with more keyword matches first)
            scored_tables = []
            for table in unique_tables:
                score = self._calculate_table_relevance(table, keywords)
                scored_tables.append((table, score))
            
            scored_tables.sort(key=lambda x: x[1], reverse=True)
            
            return [table for table, _ in scored_tables[:self.max_results]]
            
        except Exception as e:
            logger.error(f"Error searching tables by keywords: {e}")
            return []
    
    def _calculate_table_relevance(self, table: TableInfo, keywords: List[str]) -> float:
        """
        Calculate relevance score for a table based on keywords.
        
        Args:
            table: TableInfo object
            keywords: List of search keywords
            
        Returns:
            Relevance score (higher = more relevant)
        """
        score = 0.0
        
        # Check table name
        table_name_lower = table.name.lower()
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower == table_name_lower:
                score += 10.0  # Exact match
            elif keyword_lower in table_name_lower:
                score += 5.0   # Partial match
        
        # Check comment/description
        if table.comment:
            comment_lower = table.comment.lower()
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in comment_lower:
                    score += 2.0
        
        # Check schema name
        schema_lower = table.schema.lower()
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in schema_lower:
                score += 1.0
        
        return score
    
    def _analyze_tables_with_ai(self, processed_query: ProcessedQuery, 
                               tables: List[TableInfo]) -> Dict[str, Any]:
        """
        Use AI to analyze the discovered tables.
        
        Args:
            processed_query: Original processed query
            tables: List of discovered tables
            
        Returns:
            AI analysis results
        """
        try:
            # Prepare table information for AI
            table_info = []
            for table in tables:
                table_info.append({
                    'table_name': table.name,
                    'schema_name': table.schema,
                    'database_name': table.database,
                    'table_type': table.table_type,
                    'row_count': table.row_count,
                    'comment': table.comment or 'No description available'
                })
            
            # Get AI analysis
            ai_response = self.cortex_client.analyze_table_discovery(
                processed_query.original_query,
                table_info
            )
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error in AI table analysis: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': 'Unable to generate AI analysis at this time.'
            }
    
    def _generate_suggestions(self, processed_query: ProcessedQuery, 
                            tables: List[TableInfo]) -> List[str]:
        """
        Generate suggestions for further exploration.
        
        Args:
            processed_query: Original processed query
            tables: Discovered tables
            
        Returns:
            List of suggestion strings
        """
        suggestions = []
        
        if not tables:
            suggestions.extend([
                "Try using different keywords",
                "Check the spelling of your search terms",
                "Ask to see all available tables",
                "Be more specific about the type of data you're looking for"
            ])
        else:
            # Suggest exploring specific tables
            if len(tables) > 0:
                top_table = tables[0]
                suggestions.append(f"Show me the columns in {top_table.schema}.{top_table.name}")
                suggestions.append(f"Give me a sample of data from {top_table.name}")
            
            if len(tables) > 1:
                suggestions.append("Compare the structure of these tables")
            
            # General suggestions
            suggestions.extend([
                "Show me recent data from these tables",
                "Help me understand what data is available",
                "Suggest queries I can run on these tables"
            ])
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def _format_table_info(self, table: TableInfo) -> Dict[str, Any]:
        """
        Format table information for display.
        
        Args:
            table: TableInfo object
            
        Returns:
            Formatted table information dictionary
        """
        return {
            'name': table.name,
            'schema': table.schema,
            'database': table.database,
            'full_name': table.full_name,
            'type': table.table_type,
            'row_count': table.row_count,
            'comment': table.comment,
            'created_on': table.created_on.isoformat() if table.created_on else None,
            'last_altered': table.last_altered.isoformat() if table.last_altered else None
        }
    
    def get_table_details(self, table_name: str, schema_name: str = None) -> Dict[str, Any]:
        """
        Get detailed information about a specific table.
        
        Args:
            table_name: Name of the table
            schema_name: Optional schema name
            
        Returns:
            Detailed table information including columns
        """
        try:
            # Get column information
            columns = self.snowflake_client.get_table_columns(table_name, schema_name)
            
            # Get table info
            tables = self.snowflake_client.get_tables(
                schema_pattern=schema_name,
                table_pattern=table_name
            )
            
            table_info = tables[0] if tables else None
            
            return {
                'table_info': self._format_table_info(table_info) if table_info else None,
                'columns': [
                    {
                        'name': col.name,
                        'data_type': col.data_type,
                        'is_nullable': col.is_nullable,
                        'default_value': col.default_value,
                        'comment': col.comment
                    }
                    for col in columns
                ],
                'column_count': len(columns)
            }
            
        except Exception as e:
            logger.error(f"Error getting table details: {e}")
            return {
                'error': str(e),
                'table_info': None,
                'columns': [],
                'column_count': 0
            }
    
    def _get_supported_intents(self) -> List[str]:
        """Get list of intents this agent supports."""
        return ['table_discovery', 'general_query']

