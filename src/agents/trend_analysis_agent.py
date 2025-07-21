"""
Trend analysis agent for analyzing data trends and patterns.
"""

import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd

from .base_agent import BaseAgent, AgentResult
from ..processing.query_processor import ProcessedQuery
from ..database.query_builder import QueryBuilder

logger = logging.getLogger(__name__)

class TrendAnalysisAgent(BaseAgent):
    """
    Agent specialized in analyzing trends and patterns in time-series data.
    """
    
    def __init__(self):
        """Initialize the trend analysis agent."""
        super().__init__(
            name="Trend Analysis Agent",
            description="Analyzes production trends and generates insights from time-series data"
        )
        
        # Agent-specific configuration
        self.time_periods = self.config.get('time_periods', ['1M', '3M', '6M', '1Y', '2Y'])
        self.default_period = self.config.get('default_period', '1Y')
    
    def can_handle(self, processed_query: ProcessedQuery) -> bool:
        """
        Determine if this agent can handle the query.
        
        Args:
            processed_query: ProcessedQuery object
            
        Returns:
            True if this agent can handle the query
        """
        # Handle trend analysis intents
        if processed_query.intent == 'trend_analysis':
            return True
        
        # Also handle queries with trend-related keywords
        trend_keywords = {
            'trend', 'trends', 'analysis', 'production', 'performance', 
            'over time', 'last', 'past', 'previous', 'fy', 'year', 'month'
        }
        
        query_lower = processed_query.original_query.lower()
        return any(keyword in query_lower for keyword in trend_keywords)
    
    def execute(self, processed_query: ProcessedQuery) -> AgentResult:
        """
        Execute trend analysis based on the processed query.
        
        Args:
            processed_query: ProcessedQuery object
            
        Returns:
            AgentResult with trend analysis results
        """
        start_time = time.time()
        
        try:
            # Validate the query
            if not self.validate_query(processed_query):
                return AgentResult(
                    success=False,
                    data=None,
                    message="Invalid query for trend analysis",
                    suggestions=["Please specify what data you want to analyze trends for"],
                    metadata={},
                    execution_time=time.time() - start_time,
                    agent_name=self.name
                )
            
            # Extract time period from query
            time_period = self._extract_time_period(processed_query)
            
            # Find relevant tables for trend analysis
            relevant_tables = self._find_trend_tables(processed_query)
            
            if not relevant_tables:
                return self._handle_no_tables_found(processed_query, start_time)
            
            # Analyze trends in the data
            trend_results = self._analyze_trends(processed_query, relevant_tables, time_period)
            
            # Generate AI insights
            ai_insights = self._generate_ai_insights(processed_query, trend_results)
            
            # Generate suggestions
            suggestions = self._generate_suggestions(processed_query, trend_results)
            
            # Prepare result data
            result_data = {
                'trend_analysis': trend_results,
                'time_period': time_period,
                'tables_analyzed': len(relevant_tables),
                'ai_insights': ai_insights,
                'relevant_tables': [table['name'] for table in relevant_tables]
            }
            
            message = self._generate_summary_message(trend_results, time_period)
            
            execution_time = time.time() - start_time
            
            return AgentResult(
                success=True,
                data=result_data,
                message=message,
                suggestions=suggestions,
                metadata={
                    'time_period': time_period,
                    'tables_count': len(relevant_tables),
                    'ai_insights_success': ai_insights.get('success', False)
                },
                execution_time=execution_time,
                agent_name=self.name
            )
            
        except Exception as e:
            return self.handle_error(e, processed_query)
    
    def _extract_time_period(self, processed_query: ProcessedQuery) -> str:
        """
        Extract time period from the processed query.
        
        Args:
            processed_query: ProcessedQuery object
            
        Returns:
            Time period string (e.g., '1Y', '6M')
        """
        time_period_info = processed_query.processing_metadata.get('time_period')
        
        if time_period_info:
            period_value = time_period_info.get('value', '').lower()
            
            # Map common period expressions to our format
            if 'fy' in period_value or 'fiscal year' in period_value:
                return '1Y'
            elif 'year' in period_value:
                return '1Y'
            elif '6 month' in period_value or 'half year' in period_value:
                return '6M'
            elif '3 month' in period_value or 'quarter' in period_value:
                return '3M'
            elif 'month' in period_value:
                return '1M'
        
        return self.default_period
    
    def _find_trend_tables(self, processed_query: ProcessedQuery) -> List[Dict[str, Any]]:
        """
        Find tables that are suitable for trend analysis.
        
        Args:
            processed_query: ProcessedQuery object
            
        Returns:
            List of table information dictionaries
        """
        try:
            # Look for tables that might contain time-series data
            trend_keywords = processed_query.keywords.primary_keywords + ['production', 'sales', 'performance']
            
            relevant_tables = []
            
            for keyword in trend_keywords:
                tables = self.snowflake_client.search_tables_by_keyword(keyword, limit=10)
                
                for table in tables:
                    # Check if table has date columns (basic heuristic)
                    columns = self.snowflake_client.get_table_columns(table.name, table.schema)
                    
                    date_columns = [
                        col for col in columns 
                        if any(date_indicator in col.name.lower() 
                              for date_indicator in ['date', 'time', 'created', 'updated', 'timestamp'])
                    ]
                    
                    if date_columns and table.row_count and table.row_count > 0:
                        relevant_tables.append({
                            'name': table.name,
                            'schema': table.schema,
                            'database': table.database,
                            'full_name': table.full_name,
                            'row_count': table.row_count,
                            'date_columns': [col.name for col in date_columns],
                            'all_columns': [col.name for col in columns]
                        })
            
            # Remove duplicates
            seen_tables = set()
            unique_tables = []
            for table in relevant_tables:
                table_key = table['full_name']
                if table_key not in seen_tables:
                    seen_tables.add(table_key)
                    unique_tables.append(table)
            
            return unique_tables[:5]  # Limit to top 5 tables
            
        except Exception as e:
            logger.error(f"Error finding trend tables: {e}")
            return []
    
    def _analyze_trends(self, processed_query: ProcessedQuery, 
                       tables: List[Dict[str, Any]], time_period: str) -> Dict[str, Any]:
        """
        Analyze trends in the identified tables.
        
        Args:
            processed_query: ProcessedQuery object
            tables: List of table information
            time_period: Time period for analysis
            
        Returns:
            Trend analysis results
        """
        trend_results = {
            'period': time_period,
            'tables_analyzed': [],
            'summary_stats': {},
            'trends_found': []
        }
        
        try:
            for table in tables:
                table_trends = self._analyze_single_table_trends(table, time_period)
                if table_trends:
                    trend_results['tables_analyzed'].append(table_trends)
            
            # Generate summary statistics
            trend_results['summary_stats'] = self._calculate_summary_stats(trend_results['tables_analyzed'])
            
            # Identify key trends
            trend_results['trends_found'] = self._identify_key_trends(trend_results['tables_analyzed'])
            
        except Exception as e:
            logger.error(f"Error analyzing trends: {e}")
            trend_results['error'] = str(e)
        
        return trend_results
    
    def _analyze_single_table_trends(self, table: Dict[str, Any], time_period: str) -> Optional[Dict[str, Any]]:
        """
        Analyze trends in a single table.
        
        Args:
            table: Table information dictionary
            time_period: Time period for analysis
            
        Returns:
            Trend analysis for the table or None if analysis fails
        """
        try:
            # Use the first date column found
            date_column = table['date_columns'][0] if table['date_columns'] else None
            if not date_column:
                return None
            
            # Find a numeric column to analyze
            numeric_columns = []
            for col_name in table['all_columns']:
                if any(indicator in col_name.lower() 
                      for indicator in ['count', 'amount', 'value', 'total', 'sum', 'revenue', 'sales']):
                    numeric_columns.append(col_name)
            
            if not numeric_columns:
                # Use row count as a fallback metric
                value_column = 'COUNT(*)'
                aggregation = 'COUNT'
            else:
                value_column = numeric_columns[0]
                aggregation = 'SUM'
            
            # Build and execute trend query
            query, params = QueryBuilder.build_trend_analysis_query(
                table['full_name'],
                date_column,
                value_column,
                time_period,
                aggregation
            )
            
            result = self.snowflake_client.execute_query(query, params)
            
            if result.success and not result.data.empty:
                # Calculate trend metrics
                data = result.data
                trend_metrics = self._calculate_trend_metrics(data)
                
                return {
                    'table_name': table['name'],
                    'full_name': table['full_name'],
                    'date_column': date_column,
                    'value_column': value_column,
                    'aggregation': aggregation,
                    'data_points': len(data),
                    'trend_metrics': trend_metrics,
                    'sample_data': data.head(10).to_dict('records')
                }
            
        except Exception as e:
            logger.error(f"Error analyzing table {table['name']}: {e}")
        
        return None
    
    def _calculate_trend_metrics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate trend metrics from time-series data.
        
        Args:
            data: DataFrame with time-series data
            
        Returns:
            Dictionary of trend metrics
        """
        if data.empty or 'VALUE' not in data.columns:
            return {}
        
        values = data['VALUE'].dropna()
        
        if len(values) < 2:
            return {'error': 'Insufficient data points for trend analysis'}
        
        # Basic trend metrics
        metrics = {
            'total_periods': len(values),
            'min_value': float(values.min()),
            'max_value': float(values.max()),
            'avg_value': float(values.mean()),
            'std_value': float(values.std()),
            'first_value': float(values.iloc[0]),
            'last_value': float(values.iloc[-1])
        }
        
        # Calculate trend direction
        if metrics['last_value'] > metrics['first_value']:
            metrics['trend_direction'] = 'increasing'
            metrics['total_change'] = metrics['last_value'] - metrics['first_value']
            metrics['percent_change'] = ((metrics['last_value'] - metrics['first_value']) / metrics['first_value']) * 100
        elif metrics['last_value'] < metrics['first_value']:
            metrics['trend_direction'] = 'decreasing'
            metrics['total_change'] = metrics['last_value'] - metrics['first_value']
            metrics['percent_change'] = ((metrics['last_value'] - metrics['first_value']) / metrics['first_value']) * 100
        else:
            metrics['trend_direction'] = 'stable'
            metrics['total_change'] = 0
            metrics['percent_change'] = 0
        
        # Calculate volatility
        if len(values) > 1:
            metrics['volatility'] = float(values.std() / values.mean()) if values.mean() != 0 else 0
        
        return metrics
    
    def _calculate_summary_stats(self, table_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics across all analyzed tables."""
        if not table_analyses:
            return {}
        
        total_data_points = sum(analysis.get('data_points', 0) for analysis in table_analyses)
        
        trend_directions = [
            analysis.get('trend_metrics', {}).get('trend_direction', 'unknown')
            for analysis in table_analyses
        ]
        
        return {
            'tables_with_data': len(table_analyses),
            'total_data_points': total_data_points,
            'increasing_trends': trend_directions.count('increasing'),
            'decreasing_trends': trend_directions.count('decreasing'),
            'stable_trends': trend_directions.count('stable')
        }
    
    def _identify_key_trends(self, table_analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify the most significant trends."""
        key_trends = []
        
        for analysis in table_analyses:
            metrics = analysis.get('trend_metrics', {})
            if not metrics or 'percent_change' not in metrics:
                continue
            
            percent_change = abs(metrics['percent_change'])
            
            # Consider trends with significant change as key trends
            if percent_change > 10:  # More than 10% change
                key_trends.append({
                    'table': analysis['table_name'],
                    'trend_direction': metrics['trend_direction'],
                    'percent_change': metrics['percent_change'],
                    'significance': 'high' if percent_change > 50 else 'medium'
                })
        
        # Sort by significance
        key_trends.sort(key=lambda x: abs(x['percent_change']), reverse=True)
        
        return key_trends[:5]  # Top 5 key trends
    
    def _generate_ai_insights(self, processed_query: ProcessedQuery, 
                             trend_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI insights about the trend analysis."""
        try:
            # Prepare data sample for AI analysis
            data_sample = {
                'period_analyzed': trend_results.get('period'),
                'tables_analyzed': trend_results.get('summary_stats', {}).get('tables_with_data', 0),
                'key_trends': trend_results.get('trends_found', []),
                'summary_stats': trend_results.get('summary_stats', {})
            }
            
            # Get AI analysis
            ai_response = self.cortex_client.analyze_trend_data(
                processed_query.original_query,
                data_sample,
                [{'table_name': table['table_name']} for table in trend_results.get('tables_analyzed', [])]
            )
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error generating AI insights: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': 'Unable to generate AI insights at this time.'
            }
    
    def _generate_suggestions(self, processed_query: ProcessedQuery, 
                            trend_results: Dict[str, Any]) -> List[str]:
        """Generate suggestions for further analysis."""
        suggestions = []
        
        if not trend_results.get('tables_analyzed'):
            suggestions.extend([
                "Try specifying a different time period",
                "Look for tables with date/time columns",
                "Ask to see available data tables first"
            ])
        else:
            # Suggest deeper analysis
            key_trends = trend_results.get('trends_found', [])
            if key_trends:
                top_trend = key_trends[0]
                suggestions.append(f"Analyze what caused the {top_trend['trend_direction']} trend in {top_trend['table']}")
            
            suggestions.extend([
                "Compare trends across different time periods",
                "Break down the analysis by specific categories",
                "Show me the raw data behind these trends",
                "Identify factors that influenced these changes"
            ])
        
        return suggestions[:5]
    
    def _generate_summary_message(self, trend_results: Dict[str, Any], time_period: str) -> str:
        """Generate a summary message for the trend analysis."""
        tables_count = len(trend_results.get('tables_analyzed', []))
        
        if tables_count == 0:
            return f"I couldn't find suitable data for trend analysis over the {time_period} period."
        
        summary_stats = trend_results.get('summary_stats', {})
        increasing = summary_stats.get('increasing_trends', 0)
        decreasing = summary_stats.get('decreasing_trends', 0)
        
        message = f"Analyzed trends across {tables_count} tables for the {time_period} period. "
        
        if increasing > decreasing:
            message += f"Found {increasing} increasing trends and {decreasing} decreasing trends - overall positive trend."
        elif decreasing > increasing:
            message += f"Found {decreasing} decreasing trends and {increasing} increasing trends - overall declining trend."
        else:
            message += f"Found mixed trends with {increasing} increasing and {decreasing} decreasing patterns."
        
        return message
    
    def _handle_no_tables_found(self, processed_query: ProcessedQuery, start_time: float) -> AgentResult:
        """Handle case when no suitable tables are found for trend analysis."""
        return AgentResult(
            success=False,
            data=None,
            message="I couldn't find suitable tables for trend analysis. Tables need to have date/time columns and numeric data.",
            suggestions=[
                "Ask to see available tables first",
                "Specify the table name you want to analyze",
                "Try different keywords related to your data",
                "Ask about what data is available for trend analysis"
            ],
            metadata={'reason': 'no_suitable_tables'},
            execution_time=time.time() - start_time,
            agent_name=self.name
        )
    
    def _get_supported_intents(self) -> List[str]:
        """Get list of intents this agent supports."""
        return ['trend_analysis', 'general_query']

