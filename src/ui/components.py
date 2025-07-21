"""
Reusable UI components for the Streamlit application.
"""

import logging
from typing import Dict, List, Any, Optional, Callable
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from config.settings import get_settings

logger = logging.getLogger(__name__)

class UIComponents:
    """
    Collection of reusable UI components for the Streamlit application.
    """
    
    def __init__(self):
        """Initialize UI components."""
        self.settings = get_settings()
        self.ui_config = self.settings.get_ui_config()
        self.viz_config = self.ui_config.get('visualization', {})
        
        # Color palette
        self.colors = self.viz_config.get('color_palette', [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'
        ])
    
    def render_header(self, title: str, subtitle: Optional[str] = None):
        """
        Render application header.
        
        Args:
            title: Main title
            subtitle: Optional subtitle
        """
        st.title(f"❄️ {title}")
        if subtitle:
            st.markdown(f"*{subtitle}*")
        st.markdown("---")
    
    def render_query_input(self, placeholder: str = "Ask me about your data...", 
                          key: str = "query_input") -> str:
        """
        Render query input component.
        
        Args:
            placeholder: Placeholder text
            key: Streamlit key for the input
            
        Returns:
            User input string
        """
        return st.text_input(
            "Your Question:",
            placeholder=placeholder,
            key=key,
            help="Ask questions about your data, request table information, or analyze trends"
        )
    
    def render_chat_input(self, placeholder: str = "Type your message...", 
                         key: str = "chat_input") -> str:
        """
        Render chat-style input component.
        
        Args:
            placeholder: Placeholder text
            key: Streamlit key for the input
            
        Returns:
            User input string
        """
        return st.chat_input(placeholder, key=key)
    
    def render_suggestions(self, suggestions: List[str], 
                          on_click: Optional[Callable[[str], None]] = None,
                          title: str = "💡 Suggestions"):
        """
        Render suggestion buttons.
        
        Args:
            suggestions: List of suggestion strings
            on_click: Optional callback function for suggestion clicks
            title: Title for the suggestions section
        """
        if not suggestions:
            return
        
        st.markdown(f"**{title}**")
        
        # Create columns for suggestions
        cols = st.columns(min(len(suggestions), 3))
        
        for i, suggestion in enumerate(suggestions):
            col_idx = i % len(cols)
            with cols[col_idx]:
                if st.button(
                    suggestion,
                    key=f"suggestion_{i}",
                    help=f"Click to use: {suggestion}",
                    use_container_width=True
                ):
                    if on_click:
                        on_click(suggestion)
                    else:
                        st.session_state.selected_suggestion = suggestion
    
    def render_conversation_history(self, history: List[Dict[str, Any]], 
                                   max_display: int = 10):
        """
        Render conversation history.
        
        Args:
            history: List of conversation exchanges
            max_display: Maximum number of exchanges to display
        """
        if not history:
            st.info("No conversation history yet. Start by asking a question!")
            return
        
        st.markdown("**💬 Conversation History**")
        
        # Display recent exchanges
        recent_history = history[-max_display:] if len(history) > max_display else history
        
        for i, exchange in enumerate(reversed(recent_history)):
            timestamp = exchange['timestamp'].strftime('%H:%M:%S')
            
            with st.expander(f"Exchange {len(recent_history) - i} ({timestamp})"):
                st.markdown(f"**You:** {exchange['user']}")
                st.markdown(f"**Assistant:** {exchange['assistant']}")
                
                if exchange.get('metadata'):
                    with st.expander("Details"):
                        st.json(exchange['metadata'])
    
    def render_chat_message(self, message: str, is_user: bool = False, 
                           metadata: Optional[Dict[str, Any]] = None):
        """
        Render a single chat message.
        
        Args:
            message: Message content
            is_user: Whether this is a user message
            metadata: Optional metadata to display
        """
        avatar = "🧑‍💻" if is_user else "🤖"
        
        with st.chat_message("user" if is_user else "assistant", avatar=avatar):
            st.markdown(message)
            
            if metadata and not is_user:
                with st.expander("Details", expanded=False):
                    st.json(metadata)
    
    def render_results_display(self, results: Dict[str, Any], 
                              result_type: str = "general"):
        """
        Render query results in an appropriate format.
        
        Args:
            results: Results dictionary
            result_type: Type of results (table_discovery, trend_analysis, etc.)
        """
        if not results:
            st.warning("No results to display")
            return
        
        if result_type == "table_discovery":
            self._render_table_discovery_results(results)
        elif result_type == "trend_analysis":
            self._render_trend_analysis_results(results)
        else:
            self._render_general_results(results)
    
    def _render_table_discovery_results(self, results: Dict[str, Any]):
        """Render table discovery results."""
        data = results.get('data', {})
        tables = data.get('tables', [])
        
        if not tables:
            st.info("No tables found matching your criteria")
            return
        
        st.markdown(f"**📊 Found {len(tables)} tables**")
        
        # Create DataFrame for display
        table_df = pd.DataFrame([
            {
                'Table Name': table['name'],
                'Schema': table['schema'],
                'Type': table['type'],
                'Rows': table.get('row_count', 'Unknown'),
                'Description': table.get('comment', 'No description')[:100] + '...' if table.get('comment') and len(table.get('comment', '')) > 100 else table.get('comment', 'No description')
            }
            for table in tables
        ])
        
        # Display as interactive table
        st.dataframe(
            table_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Show AI analysis if available
        ai_analysis = data.get('ai_analysis', {})
        if ai_analysis.get('success') and ai_analysis.get('response'):
            st.markdown("**🤖 AI Analysis**")
            st.markdown(ai_analysis['response'])
    
    def _render_trend_analysis_results(self, results: Dict[str, Any]):
        """Render trend analysis results."""
        data = results.get('data', {})
        trend_analysis = data.get('trend_analysis', {})
        
        if not trend_analysis:
            st.info("No trend analysis data available")
            return
        
        # Summary statistics
        summary_stats = trend_analysis.get('summary_stats', {})
        if summary_stats:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Tables Analyzed", summary_stats.get('tables_with_data', 0))
            with col2:
                st.metric("Data Points", summary_stats.get('total_data_points', 0))
            with col3:
                st.metric("Increasing Trends", summary_stats.get('increasing_trends', 0))
            with col4:
                st.metric("Decreasing Trends", summary_stats.get('decreasing_trends', 0))
        
        # Key trends
        key_trends = trend_analysis.get('trends_found', [])
        if key_trends:
            st.markdown("**📈 Key Trends**")
            
            for trend in key_trends:
                direction_emoji = "📈" if trend['trend_direction'] == 'increasing' else "📉"
                st.markdown(
                    f"{direction_emoji} **{trend['table']}**: "
                    f"{trend['trend_direction'].title()} trend "
                    f"({trend['percent_change']:+.1f}%)"
                )
        
        # Detailed analysis for each table
        tables_analyzed = trend_analysis.get('tables_analyzed', [])
        if tables_analyzed:
            st.markdown("**📊 Detailed Analysis**")
            
            for table_analysis in tables_analyzed:
                with st.expander(f"Analysis: {table_analysis['table_name']}"):
                    metrics = table_analysis.get('trend_metrics', {})
                    
                    if metrics:
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Trend Direction", metrics.get('trend_direction', 'Unknown').title())
                        with col2:
                            st.metric("Total Change", f"{metrics.get('percent_change', 0):+.1f}%")
                        with col3:
                            st.metric("Data Points", table_analysis.get('data_points', 0))
                        
                        # Sample data
                        sample_data = table_analysis.get('sample_data', [])
                        if sample_data:
                            st.markdown("**Sample Data:**")
                            st.dataframe(pd.DataFrame(sample_data), use_container_width=True)
        
        # AI insights
        ai_insights = data.get('ai_insights', {})
        if ai_insights.get('success') and ai_insights.get('response'):
            st.markdown("**🤖 AI Insights**")
            st.markdown(ai_insights['response'])
    
    def _render_general_results(self, results: Dict[str, Any]):
        """Render general results."""
        # Display main data
        data = results.get('data')
        if data:
            if isinstance(data, dict):
                st.json(data)
            elif isinstance(data, pd.DataFrame):
                st.dataframe(data, use_container_width=True)
            else:
                st.write(data)
        
        # Display metadata if available
        metadata = results.get('metadata', {})
        if metadata:
            with st.expander("Metadata"):
                st.json(metadata)
    
    def render_data_visualization(self, data: pd.DataFrame, chart_type: str = "auto",
                                 x_column: Optional[str] = None, 
                                 y_column: Optional[str] = None,
                                 title: Optional[str] = None):
        """
        Render data visualization.
        
        Args:
            data: DataFrame to visualize
            chart_type: Type of chart (line, bar, scatter, auto)
            x_column: X-axis column name
            y_column: Y-axis column name
            title: Chart title
        """
        if data.empty:
            st.info("No data available for visualization")
            return
        
        # Auto-detect columns if not specified
        if not x_column:
            # Look for date/time columns first
            date_columns = [col for col in data.columns 
                          if data[col].dtype in ['datetime64[ns]', 'object'] 
                          and 'date' in col.lower()]
            x_column = date_columns[0] if date_columns else data.columns[0]
        
        if not y_column:
            # Look for numeric columns
            numeric_columns = data.select_dtypes(include=['number']).columns
            y_column = numeric_columns[0] if len(numeric_columns) > 0 else data.columns[-1]
        
        # Auto-detect chart type if needed
        if chart_type == "auto":
            if data[x_column].dtype in ['datetime64[ns]'] or 'date' in x_column.lower():
                chart_type = "line"
            else:
                chart_type = "bar"
        
        # Create the chart
        try:
            if chart_type == "line":
                fig = px.line(data, x=x_column, y=y_column, title=title,
                             color_discrete_sequence=self.colors)
            elif chart_type == "bar":
                fig = px.bar(data, x=x_column, y=y_column, title=title,
                            color_discrete_sequence=self.colors)
            elif chart_type == "scatter":
                fig = px.scatter(data, x=x_column, y=y_column, title=title,
                               color_discrete_sequence=self.colors)
            else:
                fig = px.line(data, x=x_column, y=y_column, title=title,
                             color_discrete_sequence=self.colors)
            
            # Update layout
            fig.update_layout(
                xaxis_title=x_column.replace('_', ' ').title(),
                yaxis_title=y_column.replace('_', ' ').title(),
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            logger.error(f"Error creating visualization: {e}")
            st.error(f"Could not create visualization: {str(e)}")
    
    def render_connection_status(self, status: Dict[str, Any]):
        """
        Render connection status indicator.
        
        Args:
            status: Connection status dictionary
        """
        if not status:
            return
        
        snowflake_status = status.get('snowflake', False)
        ai_status = status.get('cortex_ai', False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            status_color = "🟢" if snowflake_status else "🔴"
            st.markdown(f"{status_color} **Snowflake**: {'Connected' if snowflake_status else 'Disconnected'}")
        
        with col2:
            status_color = "🟢" if ai_status else "🔴"
            st.markdown(f"{status_color} **Cortex AI**: {'Connected' if ai_status else 'Disconnected'}")
    
    def render_loading_spinner(self, message: str = "Processing your request..."):
        """
        Render loading spinner with message.
        
        Args:
            message: Loading message
        """
        with st.spinner(message):
            st.empty()
    
    def render_error_message(self, error: str, suggestions: Optional[List[str]] = None):
        """
        Render error message with suggestions.
        
        Args:
            error: Error message
            suggestions: Optional list of suggestions
        """
        st.error(f"❌ {error}")
        
        if suggestions:
            st.markdown("**💡 Try these suggestions:**")
            for suggestion in suggestions:
                st.markdown(f"• {suggestion}")
    
    def render_success_message(self, message: str):
        """
        Render success message.
        
        Args:
            message: Success message
        """
        st.success(f"✅ {message}")
    
    def render_info_message(self, message: str):
        """
        Render info message.
        
        Args:
            message: Info message
        """
        st.info(f"ℹ️ {message}")
    
    def render_sidebar_stats(self, stats: Dict[str, Any]):
        """
        Render session statistics in sidebar.
        
        Args:
            stats: Statistics dictionary
        """
        with st.sidebar:
            st.markdown("### 📊 Session Stats")
            
            st.metric("Total Queries", stats.get('total_queries', 0))
            st.metric("Success Rate", f"{stats.get('success_rate', 0)}%")
            st.metric("Session Duration", stats.get('session_duration', '0:00:00'))
            
            if st.button("Clear History", type="secondary"):
                return True
        
        return False
    
    def render_export_options(self, data: Any, filename: str = "export"):
        """
        Render data export options.
        
        Args:
            data: Data to export
            filename: Base filename for export
        """
        col1, col2 = st.columns(2)
        
        with col1:
            if isinstance(data, pd.DataFrame):
                csv = data.to_csv(index=False)
                st.download_button(
                    label="📄 Download CSV",
                    data=csv,
                    file_name=f"{filename}.csv",
                    mime="text/csv"
                )
        
        with col2:
            if isinstance(data, (dict, list)):
                import json
                json_str = json.dumps(data, indent=2, default=str)
                st.download_button(
                    label="📋 Download JSON",
                    data=json_str,
                    file_name=f"{filename}.json",
                    mime="application/json"
                )

