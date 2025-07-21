"""
Session management for Streamlit application.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import streamlit as st

from config.settings import get_settings

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Manages Streamlit session state and conversation history.
    """
    
    def __init__(self):
        """Initialize the session manager."""
        self.settings = get_settings()
        self.ui_config = self.settings.get_ui_config()
        self.chat_config = self.ui_config.get('chat', {})
        
        # Configuration
        self.max_history = self.chat_config.get('max_history', 50)
        self.enable_suggestions = self.chat_config.get('enable_suggestions', True)
        
        # Initialize session state
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize Streamlit session state variables."""
        # Conversation history
        if 'conversation_history' not in st.session_state:
            st.session_state.conversation_history = []
        
        # Current query and results
        if 'current_query' not in st.session_state:
            st.session_state.current_query = ""
        
        if 'current_results' not in st.session_state:
            st.session_state.current_results = None
        
        # UI state
        if 'show_suggestions' not in st.session_state:
            st.session_state.show_suggestions = self.enable_suggestions
        
        if 'selected_suggestion' not in st.session_state:
            st.session_state.selected_suggestion = None
        
        # Processing state
        if 'is_processing' not in st.session_state:
            st.session_state.is_processing = False
        
        # Connection status
        if 'connection_status' not in st.session_state:
            st.session_state.connection_status = None
        
        # User preferences
        if 'user_preferences' not in st.session_state:
            st.session_state.user_preferences = {
                'show_debug_info': False,
                'auto_suggestions': True,
                'result_format': 'table'
            }
        
        # Session metadata
        if 'session_metadata' not in st.session_state:
            st.session_state.session_metadata = {
                'session_start': datetime.now(),
                'total_queries': 0,
                'successful_queries': 0
            }
    
    def add_conversation_exchange(self, user_query: str, assistant_response: str, 
                                 metadata: Optional[Dict[str, Any]] = None):
        """
        Add a conversation exchange to the history.
        
        Args:
            user_query: User's query
            assistant_response: Assistant's response
            metadata: Optional metadata about the exchange
        """
        exchange = {
            'timestamp': datetime.now(),
            'user': user_query,
            'assistant': assistant_response,
            'metadata': metadata or {}
        }
        
        st.session_state.conversation_history.append(exchange)
        
        # Trim history if it exceeds max length
        if len(st.session_state.conversation_history) > self.max_history:
            st.session_state.conversation_history = st.session_state.conversation_history[-self.max_history:]
        
        # Update session metadata
        st.session_state.session_metadata['total_queries'] += 1
        if metadata and metadata.get('success', False):
            st.session_state.session_metadata['successful_queries'] += 1
    
    def get_conversation_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get conversation history.
        
        Args:
            limit: Optional limit on number of exchanges to return
            
        Returns:
            List of conversation exchanges
        """
        history = st.session_state.conversation_history
        
        if limit:
            return history[-limit:]
        
        return history
    
    def clear_conversation_history(self):
        """Clear the conversation history."""
        st.session_state.conversation_history = []
        st.session_state.session_metadata['total_queries'] = 0
        st.session_state.session_metadata['successful_queries'] = 0
    
    def set_current_query(self, query: str):
        """Set the current query."""
        st.session_state.current_query = query
    
    def get_current_query(self) -> str:
        """Get the current query."""
        return st.session_state.current_query
    
    def set_current_results(self, results: Any):
        """Set the current results."""
        st.session_state.current_results = results
    
    def get_current_results(self) -> Any:
        """Get the current results."""
        return st.session_state.current_results
    
    def set_processing_state(self, is_processing: bool):
        """Set the processing state."""
        st.session_state.is_processing = is_processing
    
    def is_processing(self) -> bool:
        """Check if currently processing."""
        return st.session_state.is_processing
    
    def set_connection_status(self, status: Dict[str, Any]):
        """Set the connection status."""
        st.session_state.connection_status = status
    
    def get_connection_status(self) -> Optional[Dict[str, Any]]:
        """Get the connection status."""
        return st.session_state.connection_status
    
    def update_user_preference(self, key: str, value: Any):
        """Update a user preference."""
        st.session_state.user_preferences[key] = value
    
    def get_user_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        return st.session_state.user_preferences.get(key, default)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        metadata = st.session_state.session_metadata
        history_length = len(st.session_state.conversation_history)
        
        success_rate = 0
        if metadata['total_queries'] > 0:
            success_rate = (metadata['successful_queries'] / metadata['total_queries']) * 100
        
        session_duration = datetime.now() - metadata['session_start']
        
        return {
            'session_duration': str(session_duration).split('.')[0],  # Remove microseconds
            'total_queries': metadata['total_queries'],
            'successful_queries': metadata['successful_queries'],
            'success_rate': round(success_rate, 1),
            'conversation_length': history_length,
            'session_start': metadata['session_start'].strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def export_conversation_history(self) -> str:
        """
        Export conversation history as formatted text.
        
        Returns:
            Formatted conversation history
        """
        history = self.get_conversation_history()
        
        if not history:
            return "No conversation history available."
        
        export_text = f"Snowflake AI Assistant - Conversation History\n"
        export_text += f"Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        export_text += f"Total exchanges: {len(history)}\n"
        export_text += "=" * 50 + "\n\n"
        
        for i, exchange in enumerate(history, 1):
            timestamp = exchange['timestamp'].strftime('%H:%M:%S')
            export_text += f"Exchange {i} ({timestamp}):\n"
            export_text += f"User: {exchange['user']}\n"
            export_text += f"Assistant: {exchange['assistant']}\n"
            
            if exchange.get('metadata'):
                export_text += f"Metadata: {exchange['metadata']}\n"
            
            export_text += "-" * 30 + "\n\n"
        
        return export_text
    
    def get_recent_queries(self, limit: int = 5) -> List[str]:
        """
        Get recent user queries.
        
        Args:
            limit: Number of recent queries to return
            
        Returns:
            List of recent query strings
        """
        history = self.get_conversation_history(limit)
        return [exchange['user'] for exchange in history if exchange.get('user')]
    
    def get_suggested_queries(self) -> List[str]:
        """
        Get suggested queries based on conversation history and common patterns.
        
        Returns:
            List of suggested query strings
        """
        # Base suggestions
        suggestions = [
            "Show me tables related to production",
            "Analyze production trends for the last fiscal year",
            "List all available tables",
            "Show me recent data from sales tables",
            "What tables contain customer information?"
        ]
        
        # Add context-based suggestions from recent queries
        recent_queries = self.get_recent_queries(3)
        
        for query in recent_queries:
            query_lower = query.lower()
            
            # Suggest related queries based on patterns
            if 'table' in query_lower and 'production' in query_lower:
                suggestions.append("Show me production data from the last month")
            elif 'trend' in query_lower:
                suggestions.append("Compare trends across different time periods")
            elif 'sales' in query_lower:
                suggestions.append("Analyze sales performance by region")
        
        # Remove duplicates while preserving order
        unique_suggestions = []
        seen = set()
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions[:8]  # Limit to 8 suggestions
    
    def reset_session(self):
        """Reset the entire session state."""
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Reinitialize
        self._initialize_session_state()
        
        logger.info("Session state reset")
    
    def get_context_for_query(self, current_query: str) -> Dict[str, Any]:
        """
        Get context information for the current query based on session history.
        
        Args:
            current_query: The current user query
            
        Returns:
            Context information dictionary
        """
        recent_history = self.get_conversation_history(5)
        
        # Extract context from recent exchanges
        recent_topics = []
        recent_intents = []
        
        for exchange in recent_history:
            user_query = exchange.get('user', '').lower()
            
            # Extract potential topics
            words = user_query.split()
            for word in words:
                if len(word) > 3 and word not in ['show', 'list', 'find', 'what', 'where']:
                    recent_topics.append(word)
            
            # Detect intents
            if any(keyword in user_query for keyword in ['table', 'show', 'list']):
                recent_intents.append('table_discovery')
            elif any(keyword in user_query for keyword in ['trend', 'analysis']):
                recent_intents.append('trend_analysis')
        
        return {
            'recent_topics': list(set(recent_topics)),
            'recent_intents': list(set(recent_intents)),
            'conversation_length': len(recent_history),
            'session_stats': self.get_session_stats(),
            'user_preferences': st.session_state.user_preferences
        }

