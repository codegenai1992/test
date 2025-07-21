"""
Main Streamlit application for the Snowflake AI Assistant.
"""

import logging
import traceback
from typing import Dict, Any, Optional
import streamlit as st

from config.settings import get_settings
from .session_manager import SessionManager
from .components import UIComponents
from ..services.app_service import AppService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SnowflakeAIApp:
    """
    Main Streamlit application class for the Snowflake AI Assistant.
    """
    
    def __init__(self):
        """Initialize the Streamlit application."""
        self.settings = get_settings()
        self.ui_config = self.settings.get_ui_config()
        
        # Initialize components
        self.session_manager = SessionManager()
        self.ui_components = UIComponents()
        self.app_service = AppService()
        
        # Configure Streamlit page
        self._configure_page()
        
        logger.info("Snowflake AI App initialized")
    
    def _configure_page(self):
        """Configure Streamlit page settings."""
        streamlit_config = self.ui_config.get('streamlit', {})
        
        st.set_page_config(
            page_title=streamlit_config.get('page_title', 'Snowflake AI Assistant'),
            page_icon=streamlit_config.get('page_icon', '❄️'),
            layout=streamlit_config.get('layout', 'wide'),
            initial_sidebar_state=streamlit_config.get('sidebar_state', 'expanded')
        )
    
    def run(self):
        """Run the main application."""
        try:
            # Render header
            self.ui_components.render_header(
                "Snowflake AI Assistant",
                "Intelligent data exploration and analysis powered by Cortex AI"
            )
            
            # Check connection status
            self._check_connections()
            
            # Render main interface
            self._render_main_interface()
            
            # Render sidebar
            self._render_sidebar()
            
        except Exception as e:
            logger.error(f"Application error: {e}")
            logger.error(traceback.format_exc())
            st.error(f"An unexpected error occurred: {str(e)}")
    
    def _check_connections(self):
        """Check and display connection status."""
        if not self.session_manager.get_connection_status():
            with st.spinner("Checking connections..."):
                try:
                    status = self.app_service.test_connections()
                    self.session_manager.set_connection_status(status)
                except Exception as e:
                    logger.error(f"Connection check failed: {e}")
                    status = {'snowflake': False, 'cortex_ai': False, 'error': str(e)}
                    self.session_manager.set_connection_status(status)
        
        # Display connection status
        status = self.session_manager.get_connection_status()
        if status:
            if not all([status.get('snowflake'), status.get('cortex_ai')]):
                with st.expander("⚠️ Connection Issues", expanded=True):
                    self.ui_components.render_connection_status(status)
                    if status.get('error'):
                        st.error(f"Error: {status['error']}")
    
    def _render_main_interface(self):
        """Render the main chat interface."""
        # Create tabs for different interfaces
        tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 Quick Analysis", "🔍 Advanced"])
        
        with tab1:
            self._render_chat_interface()
        
        with tab2:
            self._render_quick_analysis()
        
        with tab3:
            self._render_advanced_interface()
    
    def _render_chat_interface(self):
        """Render the chat-style interface."""
        # Display conversation history
        history = self.session_manager.get_conversation_history()
        
        # Chat container
        chat_container = st.container()
        
        with chat_container:
            # Display conversation history as chat messages
            for exchange in history:
                self.ui_components.render_chat_message(
                    exchange['user'], 
                    is_user=True
                )
                self.ui_components.render_chat_message(
                    exchange['assistant'], 
                    is_user=False,
                    metadata=exchange.get('metadata')
                )
        
        # Chat input
        user_input = self.ui_components.render_chat_input(
            placeholder="Ask me about your data...",
            key="chat_input"
        )
        
        if user_input:
            self._process_user_query(user_input, interface_type="chat")
        
        # Suggestions
        if not self.session_manager.is_processing():
            suggestions = self.session_manager.get_suggested_queries()
            if suggestions:
                st.markdown("---")
                self.ui_components.render_suggestions(
                    suggestions[:4],  # Limit to 4 suggestions in chat
                    on_click=lambda s: self._process_user_query(s, interface_type="chat"),
                    title="💡 Try asking:"
                )
    
    def _render_quick_analysis(self):
        """Render quick analysis interface."""
        st.markdown("### 🚀 Quick Analysis")
        st.markdown("Get instant insights with pre-built analysis options.")
        
        # Quick action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📋 List All Tables", use_container_width=True):
                self._process_user_query("Show me all available tables", interface_type="quick")
        
        with col2:
            if st.button("📈 Production Trends", use_container_width=True):
                self._process_user_query("Analyze production trends for the last fiscal year", interface_type="quick")
        
        with col3:
            if st.button("🔍 Search Tables", use_container_width=True):
                search_term = st.text_input("Search for tables containing:", key="table_search")
                if search_term:
                    self._process_user_query(f"Show me tables related to {search_term}", interface_type="quick")
        
        # Custom query input
        st.markdown("---")
        custom_query = self.ui_components.render_query_input(
            placeholder="Or ask a custom question...",
            key="quick_query"
        )
        
        if st.button("🔍 Analyze", type="primary") and custom_query:
            self._process_user_query(custom_query, interface_type="quick")
    
    def _render_advanced_interface(self):
        """Render advanced interface with more options."""
        st.markdown("### ⚙️ Advanced Analysis")
        
        # Advanced options
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Query Options:**")
            show_debug = st.checkbox("Show debug information", 
                                   value=self.session_manager.get_user_preference('show_debug_info', False))
            self.session_manager.update_user_preference('show_debug_info', show_debug)
            
            result_format = st.selectbox(
                "Result format:",
                ["table", "json", "summary"],
                index=0
            )
            self.session_manager.update_user_preference('result_format', result_format)
        
        with col2:
            st.markdown("**AI Options:**")
            auto_suggestions = st.checkbox("Auto-generate suggestions", 
                                         value=self.session_manager.get_user_preference('auto_suggestions', True))
            self.session_manager.update_user_preference('auto_suggestions', auto_suggestions)
        
        # Advanced query input
        st.markdown("---")
        advanced_query = st.text_area(
            "Advanced Query:",
            placeholder="Enter your detailed query here...",
            height=100,
            key="advanced_query"
        )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔍 Execute Query", type="primary") and advanced_query:
                self._process_user_query(advanced_query, interface_type="advanced")
        
        with col2:
            if st.button("🧪 Test Connection"):
                self._test_connections()
        
        with col3:
            if st.button("🔄 Reset Session"):
                self.session_manager.reset_session()
                st.rerun()
    
    def _render_sidebar(self):
        """Render sidebar with session information and controls."""
        with st.sidebar:
            st.markdown("## 📊 Session Info")
            
            # Session statistics
            stats = self.session_manager.get_session_stats()
            if self.ui_components.render_sidebar_stats(stats):
                self.session_manager.clear_conversation_history()
                st.rerun()
            
            # Export options
            st.markdown("---")
            st.markdown("### 📤 Export")
            
            if st.button("Export Conversation", use_container_width=True):
                conversation_text = self.session_manager.export_conversation_history()
                st.download_button(
                    label="📄 Download Conversation",
                    data=conversation_text,
                    file_name=f"conversation_{stats['session_start'].replace(':', '-')}.txt",
                    mime="text/plain"
                )
            
            # Connection status
            st.markdown("---")
            st.markdown("### 🔗 Connections")
            status = self.session_manager.get_connection_status()
            if status:
                self.ui_components.render_connection_status(status)
            
            # Help section
            st.markdown("---")
            st.markdown("### ❓ Help")
            
            with st.expander("How to use"):
                st.markdown("""
                **Getting Started:**
                1. Ask questions in natural language
                2. Use the suggestions for common queries
                3. Explore your data with AI assistance
                
                **Example Queries:**
                - "Show me tables related to sales"
                - "Analyze production trends for last year"
                - "What data is available?"
                """)
            
            with st.expander("Troubleshooting"):
                st.markdown("""
                **Common Issues:**
                - Check connection status above
                - Try simpler queries first
                - Use the "Test Connection" button
                - Clear session if needed
                """)
    
    def _process_user_query(self, query: str, interface_type: str = "chat"):
        """
        Process user query through the application service.
        
        Args:
            query: User query string
            interface_type: Type of interface (chat, quick, advanced)
        """
        if not query.strip():
            return
        
        # Set processing state
        self.session_manager.set_processing_state(True)
        self.session_manager.set_current_query(query)
        
        try:
            # Show processing message
            with st.spinner("🤖 Processing your request..."):
                # Get conversation context
                conversation_history = self.session_manager.get_conversation_history(5)
                context = self.session_manager.get_context_for_query(query)
                
                # Process query through app service
                result = self.app_service.process_query(
                    query, 
                    conversation_history=conversation_history,
                    context=context
                )
                
                # Store results
                self.session_manager.set_current_results(result)
                
                # Add to conversation history
                self.session_manager.add_conversation_exchange(
                    query,
                    result.message,
                    metadata={
                        'success': result.success,
                        'execution_time': result.total_execution_time,
                        'interface_type': interface_type,
                        'agent_count': len(result.agent_results)
                    }
                )
                
                # Display results
                self._display_results(result, interface_type)
                
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            logger.error(traceback.format_exc())
            
            error_message = f"I encountered an error while processing your request: {str(e)}"
            
            # Add error to conversation history
            self.session_manager.add_conversation_exchange(
                query,
                error_message,
                metadata={'success': False, 'error': str(e), 'interface_type': interface_type}
            )
            
            # Display error
            self.ui_components.render_error_message(
                str(e),
                ["Try rephrasing your question", "Check your connection", "Try a simpler query"]
            )
        
        finally:
            # Clear processing state
            self.session_manager.set_processing_state(False)
            
            # Rerun to update the interface
            if interface_type in ["quick", "advanced"]:
                st.rerun()
    
    def _display_results(self, result, interface_type: str):
        """
        Display query results.
        
        Args:
            result: WorkflowResult object
            interface_type: Type of interface
        """
        if not result.success:
            self.ui_components.render_error_message(result.message, result.suggestions)
            return
        
        # Display main message
        if interface_type == "chat":
            self.ui_components.render_chat_message(result.message, is_user=False)
        else:
            st.success(result.message)
        
        # Display results based on type
        if result.final_result and result.final_result.get('data'):
            # Determine result type from agent results
            result_type = "general"
            if result.agent_results:
                primary_agent = result.agent_results[0].agent_name
                if "Table Discovery" in primary_agent:
                    result_type = "table_discovery"
                elif "Trend Analysis" in primary_agent:
                    result_type = "trend_analysis"
            
            self.ui_components.render_results_display(
                result.final_result,
                result_type=result_type
            )
        
        # Display suggestions
        if result.suggestions and interface_type != "chat":
            self.ui_components.render_suggestions(
                result.suggestions,
                on_click=lambda s: self._process_user_query(s, interface_type),
                title="💡 Follow-up suggestions:"
            )
        
        # Display debug information if enabled
        if self.session_manager.get_user_preference('show_debug_info', False):
            with st.expander("🔧 Debug Information"):
                st.json({
                    'execution_time': result.total_execution_time,
                    'execution_path': result.execution_path,
                    'agent_count': len(result.agent_results),
                    'metadata': result.metadata
                })
    
    def _test_connections(self):
        """Test all connections and display results."""
        with st.spinner("Testing connections..."):
            try:
                status = self.app_service.test_connections()
                self.session_manager.set_connection_status(status)
                
                if all([status.get('snowflake'), status.get('cortex_ai')]):
                    self.ui_components.render_success_message("All connections are working!")
                else:
                    self.ui_components.render_error_message(
                        "Some connections failed",
                        ["Check your configuration", "Verify credentials", "Contact administrator"]
                    )
                
                self.ui_components.render_connection_status(status)
                
            except Exception as e:
                logger.error(f"Connection test failed: {e}")
                self.ui_components.render_error_message(
                    f"Connection test failed: {str(e)}",
                    ["Check your configuration", "Verify network connectivity"]
                )

def main():
    """Main entry point for the Streamlit application."""
    app = SnowflakeAIApp()
    app.run()

if __name__ == "__main__":
    main()

