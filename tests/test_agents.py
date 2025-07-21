"""
Tests for agent system components.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agents.base_agent import BaseAgent, AgentResult, AgentRegistry
from agents.table_discovery_agent import TableDiscoveryAgent
from agents.trend_analysis_agent import TrendAnalysisAgent
from processing.query_processor import ProcessedQuery
from processing.keyword_extractor import ExtractedKeywords

class TestBaseAgent:
    """Test cases for BaseAgent."""
    
    class MockAgent(BaseAgent):
        """Mock agent for testing."""
        
        def __init__(self):
            super().__init__("Mock Agent", "Test agent for unit tests")
        
        def can_handle(self, processed_query):
            return True
        
        def execute(self, processed_query):
            return AgentResult(
                success=True,
                data={"test": "data"},
                message="Mock execution successful",
                suggestions=["Test suggestion"],
                metadata={},
                execution_time=0.1,
                agent_name=self.name
            )
        
        def _get_supported_intents(self):
            return ['test_intent']
    
    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent for testing."""
        with patch('agents.base_agent.get_settings') as mock_settings:
            mock_settings.return_value.get_agent_config.return_value = {}
            mock_settings.return_value.snowflake.max_retries = 3
            mock_settings.return_value.cortex_ai.timeout = 60
            return self.MockAgent()
    
    @pytest.fixture
    def sample_processed_query(self):
        """Create a sample processed query for testing."""
        keywords = ExtractedKeywords(
            primary_keywords=['test', 'data'],
            secondary_keywords=['sample'],
            entities=['test_table'],
            intent='test_intent',
            confidence=0.8,
            original_query='Show me test data'
        )
        
        return ProcessedQuery(
            original_query='Show me test data',
            keywords=keywords,
            intent='test_intent',
            suggested_tables=['test_table'],
            query_parameters={},
            confidence=0.8,
            processing_metadata={}
        )
    
    def test_agent_initialization(self, mock_agent):
        """Test agent initialization."""
        assert mock_agent.name == "Mock Agent"
        assert mock_agent.description == "Test agent for unit tests"
        assert hasattr(mock_agent, 'snowflake_client')
        assert hasattr(mock_agent, 'cortex_client')
    
    def test_can_handle(self, mock_agent, sample_processed_query):
        """Test can_handle method."""
        assert mock_agent.can_handle(sample_processed_query) is True
    
    def test_execute(self, mock_agent, sample_processed_query):
        """Test execute method."""
        result = mock_agent.execute(sample_processed_query)
        
        assert isinstance(result, AgentResult)
        assert result.success is True
        assert result.agent_name == "Mock Agent"
        assert result.data == {"test": "data"}
    
    def test_validate_query(self, mock_agent, sample_processed_query):
        """Test query validation."""
        assert mock_agent.validate_query(sample_processed_query) is True
        
        # Test with empty query
        empty_query = ProcessedQuery(
            original_query='',
            keywords=ExtractedKeywords([], [], [], 'test', 0.0, ''),
            intent='test',
            suggested_tables=[],
            query_parameters={},
            confidence=0.0,
            processing_metadata={}
        )
        assert mock_agent.validate_query(empty_query) is False
    
    def test_handle_error(self, mock_agent, sample_processed_query):
        """Test error handling."""
        error = Exception("Test error")
        result = mock_agent.handle_error(error, sample_processed_query)
        
        assert isinstance(result, AgentResult)
        assert result.success is False
        assert "Test error" in result.metadata['error']
    
    def test_get_capabilities(self, mock_agent):
        """Test get_capabilities method."""
        capabilities = mock_agent.get_capabilities()
        
        assert capabilities['name'] == "Mock Agent"
        assert capabilities['description'] == "Test agent for unit tests"
        assert 'test_intent' in capabilities['supported_intents']

class TestAgentRegistry:
    """Test cases for AgentRegistry."""
    
    @pytest.fixture
    def registry(self):
        """Create an agent registry for testing."""
        return AgentRegistry()
    
    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent for testing."""
        agent = Mock()
        agent.name = "Test Agent"
        agent.can_handle.return_value = True
        return agent
    
    def test_register_agent(self, registry, mock_agent):
        """Test agent registration."""
        registry.register_agent(mock_agent, priority=5)
        
        assert registry.get_agent("Test Agent") == mock_agent
        assert registry._agent_priorities["Test Agent"] == 5
    
    def test_find_suitable_agents(self, registry, mock_agent):
        """Test finding suitable agents."""
        registry.register_agent(mock_agent, priority=5)
        
        # Create a mock processed query
        processed_query = Mock()
        
        suitable_agents = registry.find_suitable_agents(processed_query)
        
        assert len(suitable_agents) == 1
        assert suitable_agents[0] == mock_agent
        mock_agent.can_handle.assert_called_once_with(processed_query)
    
    def test_get_all_agents(self, registry, mock_agent):
        """Test getting all agents."""
        registry.register_agent(mock_agent)
        
        all_agents = registry.get_all_agents()
        
        assert len(all_agents) == 1
        assert all_agents[0] == mock_agent

class TestTableDiscoveryAgent:
    """Test cases for TableDiscoveryAgent."""
    
    @pytest.fixture
    def agent(self):
        """Create a TableDiscoveryAgent for testing."""
        with patch('agents.table_discovery_agent.get_settings') as mock_settings:
            mock_settings.return_value.get_agent_config.return_value = {
                'max_results': 50,
                'similarity_threshold': 0.7
            }
            mock_settings.return_value.snowflake.max_retries = 3
            mock_settings.return_value.cortex_ai.timeout = 60
            
            agent = TableDiscoveryAgent()
            
            # Mock the clients
            agent.snowflake_client = Mock()
            agent.cortex_client = Mock()
            
            return agent
    
    @pytest.fixture
    def table_discovery_query(self):
        """Create a table discovery query for testing."""
        keywords = ExtractedKeywords(
            primary_keywords=['production', 'data'],
            secondary_keywords=['table'],
            entities=[],
            intent='table_discovery',
            confidence=0.9,
            original_query='Show me tables related to production'
        )
        
        return ProcessedQuery(
            original_query='Show me tables related to production',
            keywords=keywords,
            intent='table_discovery',
            suggested_tables=[],
            query_parameters={'keywords': ['production', 'data']},
            confidence=0.9,
            processing_metadata={}
        )
    
    def test_can_handle_table_discovery(self, agent, table_discovery_query):
        """Test that agent can handle table discovery queries."""
        assert agent.can_handle(table_discovery_query) is True
    
    def test_can_handle_table_keywords(self, agent):
        """Test that agent can handle queries with table keywords."""
        keywords = ExtractedKeywords(
            primary_keywords=['show', 'tables'],
            secondary_keywords=[],
            entities=[],
            intent='general_query',
            confidence=0.7,
            original_query='show me all tables'
        )
        
        query = ProcessedQuery(
            original_query='show me all tables',
            keywords=keywords,
            intent='general_query',
            suggested_tables=[],
            query_parameters={},
            confidence=0.7,
            processing_metadata={}
        )
        
        assert agent.can_handle(query) is True
    
    def test_execute_success(self, agent, table_discovery_query):
        """Test successful execution of table discovery."""
        # Mock table search results
        from database.models import TableInfo
        mock_tables = [
            TableInfo(
                name="production_data",
                schema="public",
                database="test_db",
                table_type="BASE TABLE",
                row_count=1000,
                comment="Production data table"
            )
        ]
        
        agent._search_tables_by_keywords = Mock(return_value=mock_tables)
        agent._analyze_tables_with_ai = Mock(return_value={'success': True, 'response': 'AI analysis'})
        
        result = agent.execute(table_discovery_query)
        
        assert result.success is True
        assert result.agent_name == "Table Discovery Agent"
        assert len(result.data['tables']) == 1
        assert result.data['tables'][0]['name'] == "production_data"

class TestTrendAnalysisAgent:
    """Test cases for TrendAnalysisAgent."""
    
    @pytest.fixture
    def agent(self):
        """Create a TrendAnalysisAgent for testing."""
        with patch('agents.trend_analysis_agent.get_settings') as mock_settings:
            mock_settings.return_value.get_agent_config.return_value = {
                'time_periods': ['1M', '3M', '6M', '1Y', '2Y'],
                'default_period': '1Y'
            }
            mock_settings.return_value.snowflake.max_retries = 3
            mock_settings.return_value.cortex_ai.timeout = 60
            
            agent = TrendAnalysisAgent()
            
            # Mock the clients
            agent.snowflake_client = Mock()
            agent.cortex_client = Mock()
            
            return agent
    
    @pytest.fixture
    def trend_analysis_query(self):
        """Create a trend analysis query for testing."""
        keywords = ExtractedKeywords(
            primary_keywords=['production', 'trend'],
            secondary_keywords=['analysis'],
            entities=['fy'],
            intent='trend_analysis',
            confidence=0.9,
            original_query='Show me production trends for last FY'
        )
        
        return ProcessedQuery(
            original_query='Show me production trends for last FY',
            keywords=keywords,
            intent='trend_analysis',
            suggested_tables=[],
            query_parameters={},
            confidence=0.9,
            processing_metadata={'time_period': {'type': 'fiscal_year', 'value': 'last FY'}}
        )
    
    def test_can_handle_trend_analysis(self, agent, trend_analysis_query):
        """Test that agent can handle trend analysis queries."""
        assert agent.can_handle(trend_analysis_query) is True
    
    def test_can_handle_trend_keywords(self, agent):
        """Test that agent can handle queries with trend keywords."""
        keywords = ExtractedKeywords(
            primary_keywords=['production', 'over', 'time'],
            secondary_keywords=[],
            entities=[],
            intent='general_query',
            confidence=0.7,
            original_query='show production over time'
        )
        
        query = ProcessedQuery(
            original_query='show production over time',
            keywords=keywords,
            intent='general_query',
            suggested_tables=[],
            query_parameters={},
            confidence=0.7,
            processing_metadata={}
        )
        
        assert agent.can_handle(query) is True
    
    def test_extract_time_period(self, agent, trend_analysis_query):
        """Test time period extraction."""
        period = agent._extract_time_period(trend_analysis_query)
        assert period == '1Y'  # Should map FY to 1Y
    
    def test_execute_no_tables(self, agent, trend_analysis_query):
        """Test execution when no suitable tables are found."""
        agent._find_trend_tables = Mock(return_value=[])
        
        result = agent.execute(trend_analysis_query)
        
        assert result.success is False
        assert "couldn't find suitable tables" in result.message

if __name__ == "__main__":
    pytest.main([__file__])

