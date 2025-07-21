"""
Main application service that coordinates all components.
"""

import logging
from typing import Dict, List, Any, Optional
import time

from config.settings import get_settings
from .query_service import QueryService
from ..orchestration.workflow_manager import WorkflowManager, WorkflowResult

logger = logging.getLogger(__name__)

class AppService:
    """
    Main application service that coordinates all components of the Snowflake AI Assistant.
    """
    
    def __init__(self):
        """Initialize the application service."""
        self.settings = get_settings()
        
        # Initialize core services
        self.query_service = QueryService()
        self.workflow_manager = WorkflowManager()
        
        logger.info("Application service initialized")
    
    def process_query(self, user_query: str, 
                     conversation_history: Optional[List[Dict[str, str]]] = None,
                     context: Optional[Dict[str, Any]] = None) -> WorkflowResult:
        """
        Process a user query through the complete workflow.
        
        Args:
            user_query: User's input query
            conversation_history: Optional conversation history
            context: Optional context information
            
        Returns:
            WorkflowResult with processing results
        """
        start_time = time.time()
        
        try:
            logger.info(f"Processing query: {user_query}")
            
            # Execute the workflow
            result = self.workflow_manager.execute_workflow(
                user_query,
                conversation_history=conversation_history
            )
            
            # Add context information to metadata
            if context:
                result.metadata.update(context)
            
            logger.info(f"Query processed successfully in {result.total_execution_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            
            # Return error result
            return WorkflowResult(
                success=False,
                final_result=None,
                message=f"I encountered an error while processing your request: {str(e)}",
                suggestions=[
                    "Try rephrasing your question",
                    "Be more specific about what you're looking for",
                    "Check if your query is valid"
                ],
                execution_path=["error"],
                agent_results=[],
                total_execution_time=time.time() - start_time,
                metadata={'error': str(e), 'context': context}
            )
    
    def get_table_information(self, search_terms: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get table information, optionally filtered by search terms.
        
        Args:
            search_terms: Optional list of search terms
            
        Returns:
            Table information dictionary
        """
        try:
            if search_terms:
                return self.query_service.search_tables_by_keywords(search_terms)
            else:
                return self.query_service.get_table_information()
                
        except Exception as e:
            logger.error(f"Failed to get table information: {e}")
            return {
                'success': False,
                'tables': [],
                'error_message': str(e)
            }
    
    def get_sample_data(self, table_name: str, schema_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get sample data from a specific table.
        
        Args:
            table_name: Name of the table
            schema_name: Optional schema name
            
        Returns:
            Sample data dictionary
        """
        try:
            return self.query_service.get_sample_data(table_name, schema_name)
        except Exception as e:
            logger.error(f"Failed to get sample data: {e}")
            return {
                'success': False,
                'data': [],
                'error_message': str(e)
            }
    
    def execute_custom_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a custom SQL query.
        
        Args:
            query: SQL query string
            params: Optional query parameters
            
        Returns:
            Query result dictionary
        """
        try:
            return self.query_service.execute_database_query(query, params)
        except Exception as e:
            logger.error(f"Custom query execution failed: {e}")
            return {
                'success': False,
                'data': None,
                'error_message': str(e)
            }
    
    def generate_ai_insights(self, data: Dict[str, Any], query_context: str) -> Dict[str, Any]:
        """
        Generate AI insights about data.
        
        Args:
            data: Data to analyze
            query_context: Context about the original query
            
        Returns:
            AI insights dictionary
        """
        try:
            # Create a prompt for AI analysis
            prompt = f"""
            Analyze the following data in the context of the user's query: "{query_context}"
            
            Data summary: {str(data)[:1000]}...
            
            Please provide:
            1. Key insights about the data
            2. Notable patterns or trends
            3. Recommendations for further analysis
            4. Potential questions the user might want to ask next
            
            Keep your response concise and actionable.
            """
            
            return self.query_service.generate_ai_response(prompt)
            
        except Exception as e:
            logger.error(f"AI insights generation failed: {e}")
            return {
                'success': False,
                'response': None,
                'error_message': str(e)
            }
    
    def get_query_suggestions(self, user_context: Dict[str, Any]) -> List[str]:
        """
        Get query suggestions based on user context.
        
        Args:
            user_context: User context information
            
        Returns:
            List of suggested queries
        """
        try:
            # Base suggestions
            suggestions = [
                "Show me all available tables",
                "Analyze production trends for the last year",
                "Find tables related to sales data",
                "What data is available for analysis?",
                "Show me recent data from key tables"
            ]
            
            # Add context-based suggestions
            recent_topics = user_context.get('recent_topics', [])
            for topic in recent_topics[:3]:  # Limit to 3 recent topics
                suggestions.append(f"Show me more information about {topic}")
                suggestions.append(f"Analyze trends in {topic} data")
            
            # Remove duplicates while preserving order
            unique_suggestions = []
            seen = set()
            for suggestion in suggestions:
                if suggestion not in seen:
                    seen.add(suggestion)
                    unique_suggestions.append(suggestion)
            
            return unique_suggestions[:8]  # Limit to 8 suggestions
            
        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")
            return [
                "Show me all available tables",
                "What data can I analyze?",
                "Help me get started"
            ]
    
    def test_connections(self) -> Dict[str, Any]:
        """
        Test all system connections.
        
        Returns:
            Connection status dictionary
        """
        try:
            # Test query service connections
            query_status = self.query_service.test_connections()
            
            # Test workflow manager
            workflow_status = self.workflow_manager.test_workflow()
            
            return {
                'snowflake': query_status.get('snowflake', False),
                'cortex_ai': query_status.get('cortex_ai', False),
                'workflow_manager': workflow_status.get('test_successful', False),
                'overall': (
                    query_status.get('overall', False) and 
                    workflow_status.get('test_successful', False)
                ),
                'errors': query_status.get('errors', []),
                'details': {
                    'query_service': query_status,
                    'workflow_manager': workflow_status
                }
            }
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                'snowflake': False,
                'cortex_ai': False,
                'workflow_manager': False,
                'overall': False,
                'errors': [str(e)],
                'details': {}
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status.
        
        Returns:
            System status dictionary
        """
        try:
            # Get service statuses
            query_service_status = self.query_service.get_service_status()
            workflow_status = self.workflow_manager.get_workflow_status()
            connection_status = self.test_connections()
            
            return {
                'application': {
                    'name': self.settings.app.name,
                    'version': self.settings.app.version,
                    'debug_mode': self.settings.app.debug
                },
                'services': {
                    'query_service': query_service_status,
                    'workflow_manager': workflow_status
                },
                'connections': connection_status,
                'configuration': {
                    'snowflake_model': self.settings.cortex_ai.model,
                    'max_retries': self.settings.snowflake.max_retries,
                    'query_timeout': self.settings.snowflake.query_timeout
                },
                'health': {
                    'overall_healthy': connection_status.get('overall', False),
                    'services_running': True,
                    'last_check': time.time()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                'application': {'name': 'Snowflake AI Assistant', 'status': 'error'},
                'error': str(e),
                'health': {'overall_healthy': False}
            }
    
    def handle_feedback(self, query: str, result: WorkflowResult, 
                       feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle user feedback about query results.
        
        Args:
            query: Original user query
            result: WorkflowResult that was provided
            feedback: User feedback dictionary
            
        Returns:
            Feedback processing result
        """
        try:
            logger.info(f"Received feedback for query: {query}")
            
            # Log feedback for analysis
            feedback_data = {
                'query': query,
                'result_success': result.success,
                'execution_time': result.total_execution_time,
                'user_feedback': feedback,
                'timestamp': time.time()
            }
            
            # Here you could implement feedback storage, model improvement, etc.
            logger.info(f"Feedback logged: {feedback_data}")
            
            return {
                'success': True,
                'message': 'Thank you for your feedback! It helps us improve.',
                'feedback_id': str(int(time.time()))  # Simple feedback ID
            }
            
        except Exception as e:
            logger.error(f"Feedback handling failed: {e}")
            return {
                'success': False,
                'message': 'Failed to process feedback',
                'error': str(e)
            }
    
    def get_usage_analytics(self) -> Dict[str, Any]:
        """
        Get usage analytics (placeholder for future implementation).
        
        Returns:
            Usage analytics dictionary
        """
        # This is a placeholder for future analytics implementation
        return {
            'total_queries': 0,
            'successful_queries': 0,
            'average_response_time': 0.0,
            'most_common_intents': [],
            'popular_tables': [],
            'error_rate': 0.0,
            'note': 'Analytics implementation pending'
        }
    
    def shutdown(self):
        """Gracefully shutdown the application service."""
        try:
            logger.info("Shutting down application service...")
            
            # Close database connections
            if hasattr(self.query_service, 'snowflake_client'):
                self.query_service.snowflake_client.close_all_connections()
            
            logger.info("Application service shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            self.shutdown()
        except:
            pass  # Ignore errors during cleanup

