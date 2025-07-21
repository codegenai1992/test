"""
Integration tests for the complete system.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.app_service import AppService
from orchestration.workflow_manager import WorkflowManager
from processing.query_processor import QueryProcessor

class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        with patch('config.settings.get_settings') as mock_settings:
            settings = Mock()
            settings.app.name = "Test App"
            settings.app.version = "1.0.0"
            settings.app.log_level = "INFO"
            settings.app.debug = False
            
            settings.snowflake.max_retries = 3
            settings.snowflake.query_timeout = 300
            settings.snowflake.connection_timeout = 30
            settings.snowflake.pool_size = 5
            
            settings.cortex_ai.model = "claude-4-sonnet"
            settings.cortex_ai.max_tokens = 4000
            settings.cortex_ai.temperature = 0.1
            settings.cortex_ai.timeout = 60
            settings.cortex_ai.max_retries = 3
            
            settings.get_snowflake_connection_params.return_value = {
                'account': 'test_account',
                'user': 'test_user',
                'password': 'test_password',
                'warehouse': 'test_warehouse',
                'database': 'test_database',
                'schema': 'test_schema'
            }
            
            settings.get_agent_config.return_value = {}
            settings.get_processing_config.return_value = {}
            settings.get_ui_config.return_value = {}
            
            mock_settings.return_value = settings
            return settings
    
    @pytest.fixture
    def app_service(self, mock_settings):
        """Create an AppService for testing."""
        with patch('services.app_service.QueryService') as mock_query_service, \
             patch('services.app_service.WorkflowManager') as mock_workflow_manager:
            
            # Mock query service
            query_service_instance = Mock()
            query_service_instance.test_connections.return_value = {
                'snowflake': True,
                'cortex_ai': True,
                'overall': True,
                'errors': []
            }
            mock_query_service.return_value = query_service_instance
            
            # Mock workflow manager
            workflow_manager_instance = Mock()
            workflow_manager_instance.test_workflow.return_value = {
                'test_successful': True,
                'execution_time': 0.5
            }
            mock_workflow_manager.return_value = workflow_manager_instance
            
            app_service = AppService()
            app_service.query_service = query_service_instance
            app_service.workflow_manager = workflow_manager_instance
            
            return app_service
    
    def test_table_discovery_workflow(self, app_service):
        """Test complete table discovery workflow."""
        # Mock workflow result
        from orchestration.workflow_manager import WorkflowResult
        from agents.base_agent import AgentResult
        
        agent_result = AgentResult(
            success=True,
            data={
                'tables': [
                    {
                        'name': 'production_data',
                        'schema': 'public',
                        'database': 'test_db',
                        'type': 'BASE TABLE',
                        'row_count': 1000,
                        'comment': 'Production data table'
                    }
                ],
                'search_terms': ['production'],
                'total_count': 1
            },
            message="Found 1 table related to production",
            suggestions=["Show me columns in production_data", "Get sample data from production_data"],
            metadata={'search_terms': ['production']},
            execution_time=0.5,
            agent_name="Table Discovery Agent"
        )
        
        workflow_result = WorkflowResult(
            success=True,
            final_result={
                'success': True,
                'data': agent_result.data,
                'message': agent_result.message,
                'suggestions': agent_result.suggestions
            },
            message=agent_result.message,
            suggestions=agent_result.suggestions,
            execution_path=['query_processing', 'agent_selection', 'agent_execution', 'result_synthesis'],
            agent_results=[agent_result],
            total_execution_time=0.8,
            metadata={}
        )
        
        app_service.workflow_manager.execute_workflow.return_value = workflow_result
        
        # Execute the workflow
        result = app_service.process_query("Show me tables related to production")
        
        assert result.success is True
        assert "Found 1 table" in result.message
        assert len(result.agent_results) == 1
        assert result.agent_results[0].agent_name == "Table Discovery Agent"
    
    def test_trend_analysis_workflow(self, app_service):
        """Test complete trend analysis workflow."""
        from orchestration.workflow_manager import WorkflowResult
        from agents.base_agent import AgentResult
        
        agent_result = AgentResult(
            success=True,
            data={
                'trend_analysis': {
                    'period': '1Y',
                    'summary_stats': {
                        'tables_with_data': 2,
                        'increasing_trends': 1,
                        'decreasing_trends': 1
                    },
                    'trends_found': [
                        {
                            'table': 'production_metrics',
                            'trend_direction': 'increasing',
                            'percent_change': 15.5
                        }
                    ]
                },
                'time_period': '1Y',
                'tables_analyzed': 2
            },
            message="Analyzed trends across 2 tables for the 1Y period",
            suggestions=["Analyze what caused the increasing trend", "Compare with previous year"],
            metadata={'time_period': '1Y'},
            execution_time=1.2,
            agent_name="Trend Analysis Agent"
        )
        
        workflow_result = WorkflowResult(
            success=True,
            final_result={
                'success': True,
                'data': agent_result.data,
                'message': agent_result.message,
                'suggestions': agent_result.suggestions
            },
            message=agent_result.message,
            suggestions=agent_result.suggestions,
            execution_path=['query_processing', 'agent_selection', 'agent_execution', 'result_synthesis'],
            agent_results=[agent_result],
            total_execution_time=1.5,
            metadata={}
        )
        
        app_service.workflow_manager.execute_workflow.return_value = workflow_result
        
        # Execute the workflow
        result = app_service.process_query("Show me production trends for last FY")
        
        assert result.success is True
        assert "Analyzed trends" in result.message
        assert len(result.agent_results) == 1
        assert result.agent_results[0].agent_name == "Trend Analysis Agent"
    
    def test_error_handling_workflow(self, app_service):
        """Test error handling in the workflow."""
        from orchestration.workflow_manager import WorkflowResult
        
        # Mock workflow failure
        workflow_result = WorkflowResult(
            success=False,
            final_result=None,
            message="I encountered an error while processing your request: Connection failed",
            suggestions=["Try rephrasing your question", "Check your connection"],
            execution_path=['error'],
            agent_results=[],
            total_execution_time=0.1,
            metadata={'error': 'Connection failed'}
        )
        
        app_service.workflow_manager.execute_workflow.return_value = workflow_result
        
        # Execute the workflow
        result = app_service.process_query("Invalid query that causes error")
        
        assert result.success is False
        assert "error" in result.message.lower()
        assert len(result.suggestions) > 0
    
    def test_connection_testing(self, app_service):
        """Test connection testing functionality."""
        # Test successful connections
        status = app_service.test_connections()
        
        assert status['snowflake'] is True
        assert status['cortex_ai'] is True
        assert status['overall'] is True
        assert len(status['errors']) == 0
    
    def test_system_status(self, app_service):
        """Test system status reporting."""
        status = app_service.get_system_status()
        
        assert 'application' in status
        assert 'services' in status
        assert 'connections' in status
        assert 'health' in status
        assert status['application']['name'] == "Test App"

class TestQueryProcessingPipeline:
    """Test the query processing pipeline."""
    
    @pytest.fixture
    def query_processor(self):
        """Create a QueryProcessor for testing."""
        with patch('processing.query_processor.get_settings') as mock_settings:
            mock_settings.return_value.get_processing_config.return_value = {
                'keyword_extraction': {
                    'min_keyword_length': 3,
                    'max_keywords': 10,
                    'stop_words_enabled': True,
                    'stemming_enabled': True
                },
                'data_normalization': {
                    'date_formats': ['%Y-%m-%d'],
                    'numeric_precision': 2,
                    'text_case': 'lower'
                }
            }
            
            processor = QueryProcessor()
            
            # Mock the components
            processor.keyword_extractor = Mock()
            processor.data_normalizer = Mock()
            
            return processor
    
    def test_table_discovery_query_processing(self, query_processor):
        """Test processing of table discovery queries."""
        from processing.keyword_extractor import ExtractedKeywords
        
        # Mock keyword extraction
        keywords = ExtractedKeywords(
            primary_keywords=['tables', 'production'],
            secondary_keywords=['related'],
            entities=[],
            intent='table_discovery',
            confidence=0.9,
            original_query='Show me tables related to production'
        )
        
        query_processor.keyword_extractor.extract_keywords.return_value = keywords
        query_processor.keyword_extractor.extract_time_period.return_value = None
        query_processor.keyword_extractor.extract_table_references.return_value = []
        query_processor.keyword_extractor.get_search_terms.return_value = ['tables', 'production']
        
        # Mock data normalization
        query_processor.data_normalizer.normalize_query_parameters.return_value = {
            'keywords': ['tables', 'production'],
            'primary_keywords': ['tables', 'production'],
            'secondary_keywords': ['related'],
            'entities': []
        }
        
        # Process the query
        result = query_processor.process_user_query('Show me tables related to production')
        
        assert result.intent == 'table_discovery'
        assert result.confidence > 0.8
        assert 'production' in result.keywords.primary_keywords
    
    def test_trend_analysis_query_processing(self, query_processor):
        """Test processing of trend analysis queries."""
        from processing.keyword_extractor import ExtractedKeywords
        
        # Mock keyword extraction
        keywords = ExtractedKeywords(
            primary_keywords=['production', 'trend'],
            secondary_keywords=['analysis'],
            entities=['fy'],
            intent='trend_analysis',
            confidence=0.9,
            original_query='Analyze production trends for last FY'
        )
        
        query_processor.keyword_extractor.extract_keywords.return_value = keywords
        query_processor.keyword_extractor.extract_time_period.return_value = {
            'type': 'fiscal_year',
            'value': 'last FY'
        }
        query_processor.keyword_extractor.extract_table_references.return_value = []
        query_processor.keyword_extractor.get_search_terms.return_value = ['production', 'trend']
        
        # Mock data normalization
        query_processor.data_normalizer.normalize_query_parameters.return_value = {
            'keywords': ['production', 'trend'],
            'primary_keywords': ['production', 'trend'],
            'secondary_keywords': ['analysis'],
            'entities': ['fy'],
            'time_period': {'type': 'fiscal_year', 'value': 'last FY'}
        }
        
        # Process the query
        result = query_processor.process_user_query('Analyze production trends for last FY')
        
        assert result.intent == 'trend_analysis'
        assert result.confidence > 0.8
        assert result.processing_metadata['time_period']['type'] == 'fiscal_year'

class TestServiceIntegration:
    """Test integration between different services."""
    
    @pytest.fixture
    def mock_services(self):
        """Mock all services for integration testing."""
        with patch('services.query_service.SnowflakeClient') as mock_sf_client, \
             patch('services.query_service.CortexAIClient') as mock_ai_client, \
             patch('services.query_service.QueryProcessor') as mock_processor:
            
            # Mock Snowflake client
            sf_instance = Mock()
            sf_instance.test_connection.return_value = True
            sf_instance.execute_query.return_value = Mock(success=True, data=Mock(), columns=[])
            mock_sf_client.return_value = sf_instance
            
            # Mock AI client
            ai_instance = Mock()
            ai_instance.test_connection.return_value = True
            ai_instance.complete.return_value = {'success': True, 'response': 'AI response'}
            mock_ai_client.return_value = ai_instance
            
            # Mock processor
            processor_instance = Mock()
            mock_processor.return_value = processor_instance
            
            return {
                'snowflake': sf_instance,
                'ai': ai_instance,
                'processor': processor_instance
            }
    
    def test_query_service_integration(self, mock_services):
        """Test QueryService integration with its dependencies."""
        from services.query_service import QueryService
        
        with patch('services.query_service.get_settings') as mock_settings:
            mock_settings.return_value.snowflake.max_retries = 3
            mock_settings.return_value.cortex_ai.timeout = 60
            
            service = QueryService()
            
            # Test database query execution
            result = service.execute_database_query("SELECT * FROM test_table")
            assert result['success'] is True
            
            # Test AI response generation
            ai_result = service.generate_ai_response("Test prompt")
            assert ai_result['success'] is True
            
            # Test connection testing
            status = service.test_connections()
            assert status['overall'] is True

if __name__ == "__main__":
    pytest.main([__file__])

