"""
Snowflake Cortex AI client for Claude 4 Sonnet integration.
"""

import time
import logging
from typing import Dict, List, Any, Optional, Union
import json

from config.settings import get_settings
from ..database.snowflake_client import SnowflakeClient
from .prompt_templates import PromptTemplates, PromptContext

logger = logging.getLogger(__name__)

class CortexAIClient:
    """
    Client for interacting with Snowflake Cortex AI services.
    """
    
    def __init__(self, snowflake_client: Optional[SnowflakeClient] = None):
        """
        Initialize Cortex AI client.
        
        Args:
            snowflake_client: Optional SnowflakeClient instance
        """
        self.settings = get_settings()
        self.snowflake_client = snowflake_client or SnowflakeClient()
        self.prompt_templates = PromptTemplates()
        
        # Configuration
        self.model = self.settings.cortex_ai.model
        self.max_tokens = self.settings.cortex_ai.max_tokens
        self.temperature = self.settings.cortex_ai.temperature
        self.timeout = self.settings.cortex_ai.timeout
        self.max_retries = self.settings.cortex_ai.max_retries
    
    def complete(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generate completion using Snowflake Cortex AI.
        
        Args:
            prompt: Input prompt for the AI model
            **kwargs: Additional parameters for the model
            
        Returns:
            Dictionary containing the AI response and metadata
        """
        start_time = time.time()
        
        # Override default parameters with kwargs
        model = kwargs.get('model', self.model)
        max_tokens = kwargs.get('max_tokens', self.max_tokens)
        temperature = kwargs.get('temperature', self.temperature)
        
        # Build the Cortex AI query
        cortex_query = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            '{model}',
            [
                {{'role': 'system', 'content': '{self._escape_sql_string(self.prompt_templates.get_system_prompt())}'}},
                {{'role': 'user', 'content': '{self._escape_sql_string(prompt)}'}}
            ],
            {{
                'max_tokens': {max_tokens},
                'temperature': {temperature}
            }}
        ) as response
        """
        
        try:
            # Execute the query
            result = self.snowflake_client.execute_query(cortex_query)
            
            if not result.success:
                logger.error(f"Cortex AI query failed: {result.error_message}")
                return {
                    'success': False,
                    'error': result.error_message,
                    'response': None,
                    'execution_time': time.time() - start_time
                }
            
            # Extract the response
            if not result.data.empty:
                response_text = result.data.iloc[0]['RESPONSE']
                
                return {
                    'success': True,
                    'response': response_text,
                    'model': model,
                    'execution_time': time.time() - start_time,
                    'metadata': {
                        'max_tokens': max_tokens,
                        'temperature': temperature,
                        'query_id': result.metadata.get('query_id')
                    }
                }
            else:
                return {
                    'success': False,
                    'error': 'Empty response from Cortex AI',
                    'response': None,
                    'execution_time': time.time() - start_time
                }
                
        except Exception as e:
            logger.error(f"Error calling Cortex AI: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': None,
                'execution_time': time.time() - start_time
            }
    
    def analyze_table_discovery(self, user_query: str, table_info: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze table discovery results using AI.
        
        Args:
            user_query: Original user query
            table_info: List of table information dictionaries
            
        Returns:
            AI analysis of the table discovery results
        """
        context = PromptContext(
            user_query=user_query,
            intent='table_discovery',
            keywords=[],  # Will be populated by the calling code
            table_info=table_info
        )
        
        prompt = self.prompt_templates.get_table_discovery_prompt(context)
        return self.complete(prompt)
    
    def analyze_trend_data(self, user_query: str, data_sample: Dict[str, Any], 
                          table_info: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Analyze trend data using AI.
        
        Args:
            user_query: Original user query
            data_sample: Sample of the trend data
            table_info: Optional table information
            
        Returns:
            AI analysis of the trend data
        """
        context = PromptContext(
            user_query=user_query,
            intent='trend_analysis',
            keywords=[],  # Will be populated by the calling code
            data_sample=data_sample,
            table_info=table_info
        )
        
        prompt = self.prompt_templates.get_trend_analysis_prompt(context)
        return self.complete(prompt)
    
    def explain_query_results(self, user_query: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate explanation for query results.
        
        Args:
            user_query: Original user query
            results: Query results to explain
            
        Returns:
            AI explanation of the results
        """
        context = PromptContext(
            user_query=user_query,
            intent='data_explanation',
            keywords=[],
            data_sample=results
        )
        
        prompt = self.prompt_templates.get_data_explanation_prompt(context)
        return self.complete(prompt)
    
    def suggest_queries(self, user_query: str, table_info: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Suggest SQL queries based on user intent.
        
        Args:
            user_query: Original user query
            table_info: Available table information
            
        Returns:
            AI-generated query suggestions
        """
        context = PromptContext(
            user_query=user_query,
            intent='query_suggestion',
            keywords=[],
            table_info=table_info
        )
        
        prompt = self.prompt_templates.get_query_suggestion_prompt(context)
        return self.complete(prompt)
    
    def handle_conversational_query(self, user_query: str, conversation_history: List[Dict[str, str]],
                                  keywords: List[str]) -> Dict[str, Any]:
        """
        Handle conversational queries with context.
        
        Args:
            user_query: Current user query
            conversation_history: Previous conversation exchanges
            keywords: Extracted keywords from the query
            
        Returns:
            AI response for conversational interaction
        """
        context = PromptContext(
            user_query=user_query,
            intent='conversational',
            keywords=keywords,
            conversation_history=conversation_history
        )
        
        prompt = self.prompt_templates.get_conversational_prompt(context)
        return self.complete(prompt)
    
    def handle_error_gracefully(self, user_query: str, error_message: str, 
                               keywords: List[str]) -> Dict[str, Any]:
        """
        Generate helpful error messages and suggestions.
        
        Args:
            user_query: Original user query that caused the error
            error_message: The error message
            keywords: Extracted keywords
            
        Returns:
            AI-generated helpful error response
        """
        context = PromptContext(
            user_query=user_query,
            intent='error_handling',
            keywords=keywords
        )
        
        prompt = self.prompt_templates.get_error_handling_prompt(context, error_message)
        return self.complete(prompt)
    
    def generate_follow_up_suggestions(self, user_query: str, results: Dict[str, Any],
                                     intent: str) -> List[str]:
        """
        Generate follow-up question suggestions.
        
        Args:
            user_query: Original user query
            results: Query results
            intent: Detected intent
            
        Returns:
            List of follow-up question suggestions
        """
        suggestion_prompt = f"""
Based on the user's query: "{user_query}"
And the results they received, suggest 3-5 relevant follow-up questions they might want to ask.

Intent: {intent}
Results summary: {str(results)[:500]}...

Provide specific, actionable follow-up questions that would help the user explore their data further.
Format as a simple list, one question per line.
"""
        
        response = self.complete(suggestion_prompt)
        
        if response['success']:
            # Parse the response to extract individual suggestions
            suggestions_text = response['response']
            suggestions = [
                line.strip().lstrip('- ').lstrip('• ').lstrip('1234567890. ')
                for line in suggestions_text.split('\n')
                if line.strip() and not line.strip().startswith('Based on')
            ]
            return suggestions[:5]  # Limit to 5 suggestions
        else:
            # Fallback suggestions based on intent
            return self._get_fallback_suggestions(intent)
    
    def _get_fallback_suggestions(self, intent: str) -> List[str]:
        """Get fallback suggestions when AI generation fails."""
        fallback_suggestions = {
            'table_discovery': [
                "Show me the column details for the most relevant table",
                "What data is available in the last 30 days?",
                "Can you show me a sample of the data?"
            ],
            'trend_analysis': [
                "Break down the trend by month",
                "Compare this year to last year",
                "Show me the top contributing factors",
                "What caused the biggest changes?"
            ],
            'data_query': [
                "Show me more details about these results",
                "Filter the results by a specific criteria",
                "Group the data differently"
            ]
        }
        
        return fallback_suggestions.get(intent, [
            "Tell me more about this data",
            "Show me related information",
            "Help me understand what this means"
        ])
    
    def _escape_sql_string(self, text: str) -> str:
        """
        Escape string for use in SQL query.
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text safe for SQL
        """
        # Replace single quotes with double single quotes
        return text.replace("'", "''").replace("\\", "\\\\")
    
    def test_connection(self) -> bool:
        """
        Test the Cortex AI connection.
        
        Returns:
            True if connection works, False otherwise
        """
        try:
            test_response = self.complete("Hello, please respond with 'Connection successful'")
            return test_response['success'] and 'successful' in test_response.get('response', '').lower()
        except Exception as e:
            logger.error(f"Cortex AI connection test failed: {e}")
            return False

