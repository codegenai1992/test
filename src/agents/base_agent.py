"""
Base agent class for the multi-agent system.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from langchain.agents import AgentExecutor
from langchain.tools import BaseTool
from langchain.schema import BaseMessage

from config.settings import get_settings
from ..database.snowflake_client import SnowflakeClient
from ..ai.cortex_client import CortexAIClient
from ..processing.query_processor import QueryProcessor, ProcessedQuery

logger = logging.getLogger(__name__)

@dataclass
class AgentResult:
    """Result container for agent execution."""
    success: bool
    data: Any
    message: str
    suggestions: List[str]
    metadata: Dict[str, Any]
    execution_time: float
    agent_name: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'success': self.success,
            'data': self.data,
            'message': self.message,
            'suggestions': self.suggestions,
            'metadata': self.metadata,
            'execution_time': self.execution_time,
            'agent_name': self.agent_name,
            'timestamp': datetime.now().isoformat()
        }

class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.
    """
    
    def __init__(self, name: str, description: str):
        """
        Initialize the base agent.
        
        Args:
            name: Agent name
            description: Agent description
        """
        self.name = name
        self.description = description
        self.settings = get_settings()
        self.config = self.settings.get_agent_config(name.lower().replace(' ', '_'))
        
        # Initialize core components
        self.snowflake_client = SnowflakeClient()
        self.cortex_client = CortexAIClient(self.snowflake_client)
        self.query_processor = QueryProcessor()
        
        # Agent-specific configuration
        self.max_results = self.config.get('max_results', 50)
        self.similarity_threshold = self.config.get('similarity_threshold', 0.7)
        
        logger.info(f"Initialized agent: {self.name}")
    
    @abstractmethod
    def can_handle(self, processed_query: ProcessedQuery) -> bool:
        """
        Determine if this agent can handle the given query.
        
        Args:
            processed_query: ProcessedQuery object
            
        Returns:
            True if agent can handle the query, False otherwise
        """
        pass
    
    @abstractmethod
    def execute(self, processed_query: ProcessedQuery) -> AgentResult:
        """
        Execute the agent's main functionality.
        
        Args:
            processed_query: ProcessedQuery object
            
        Returns:
            AgentResult with execution results
        """
        pass
    
    def get_tools(self) -> List[BaseTool]:
        """
        Get the tools available to this agent.
        
        Returns:
            List of LangChain tools
        """
        return []
    
    def get_system_message(self) -> str:
        """
        Get the system message for this agent.
        
        Returns:
            System message string
        """
        return f"""
You are {self.name}, a specialized agent for data analysis.

Description: {self.description}

Your capabilities include:
- Analyzing user queries and determining appropriate actions
- Executing database queries through Snowflake
- Using AI to generate insights and explanations
- Providing helpful suggestions for further analysis

Always provide clear, actionable responses and suggest follow-up questions when appropriate.
"""
    
    def validate_query(self, processed_query: ProcessedQuery) -> bool:
        """
        Validate that the query is appropriate for this agent.
        
        Args:
            processed_query: ProcessedQuery object
            
        Returns:
            True if query is valid, False otherwise
        """
        # Basic validation - can be overridden by subclasses
        return (
            processed_query.original_query.strip() != "" and
            processed_query.confidence > 0.3
        )
    
    def handle_error(self, error: Exception, processed_query: ProcessedQuery) -> AgentResult:
        """
        Handle errors gracefully and provide helpful feedback.
        
        Args:
            error: The exception that occurred
            processed_query: The original processed query
            
        Returns:
            AgentResult with error information and suggestions
        """
        logger.error(f"Error in {self.name}: {error}")
        
        # Use AI to generate helpful error message
        try:
            ai_response = self.cortex_client.handle_error_gracefully(
                processed_query.original_query,
                str(error),
                processed_query.keywords.primary_keywords
            )
            
            if ai_response['success']:
                message = ai_response['response']
                suggestions = self.cortex_client.generate_follow_up_suggestions(
                    processed_query.original_query,
                    {'error': str(error)},
                    processed_query.intent
                )
            else:
                message = f"I encountered an error while processing your request: {error}"
                suggestions = self._get_fallback_error_suggestions(processed_query.intent)
        
        except Exception as ai_error:
            logger.error(f"Error generating AI error response: {ai_error}")
            message = f"I encountered an error while processing your request: {error}"
            suggestions = self._get_fallback_error_suggestions(processed_query.intent)
        
        return AgentResult(
            success=False,
            data=None,
            message=message,
            suggestions=suggestions,
            metadata={'error': str(error), 'error_type': type(error).__name__},
            execution_time=0.0,
            agent_name=self.name
        )
    
    def _get_fallback_error_suggestions(self, intent: str) -> List[str]:
        """Get fallback suggestions when error handling fails."""
        fallback_suggestions = {
            'table_discovery': [
                "Try using more specific keywords",
                "Check if the table names are spelled correctly",
                "Ask to see all available tables first"
            ],
            'trend_analysis': [
                "Specify a different time period",
                "Try a simpler query first",
                "Ask to see available data columns"
            ]
        }
        
        return fallback_suggestions.get(intent, [
            "Try rephrasing your question",
            "Be more specific about what you're looking for",
            "Ask for help with the available data"
        ])
    
    def log_execution(self, processed_query: ProcessedQuery, result: AgentResult):
        """
        Log agent execution for monitoring and debugging.
        
        Args:
            processed_query: The processed query
            result: The execution result
        """
        logger.info(
            f"Agent {self.name} executed query: '{processed_query.original_query}' "
            f"- Success: {result.success}, Time: {result.execution_time:.2f}s"
        )
        
        if not result.success:
            logger.warning(f"Agent {self.name} failed: {result.message}")
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get information about this agent's capabilities.
        
        Returns:
            Dictionary describing agent capabilities
        """
        return {
            'name': self.name,
            'description': self.description,
            'max_results': self.max_results,
            'similarity_threshold': self.similarity_threshold,
            'supported_intents': self._get_supported_intents(),
            'tools': [tool.name for tool in self.get_tools()],
            'config': self.config
        }
    
    @abstractmethod
    def _get_supported_intents(self) -> List[str]:
        """
        Get list of intents this agent supports.
        
        Returns:
            List of supported intent strings
        """
        pass
    
    def test_connection(self) -> bool:
        """
        Test connections to required services.
        
        Returns:
            True if all connections are working, False otherwise
        """
        try:
            # Test Snowflake connection
            if not self.snowflake_client.test_connection():
                logger.error(f"Snowflake connection test failed for {self.name}")
                return False
            
            # Test Cortex AI connection
            if not self.cortex_client.test_connection():
                logger.error(f"Cortex AI connection test failed for {self.name}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Connection test failed for {self.name}: {e}")
            return False

class AgentRegistry:
    """
    Registry for managing available agents.
    """
    
    def __init__(self):
        """Initialize the agent registry."""
        self._agents: Dict[str, BaseAgent] = {}
        self._agent_priorities: Dict[str, int] = {}
    
    def register_agent(self, agent: BaseAgent, priority: int = 0):
        """
        Register an agent with the registry.
        
        Args:
            agent: Agent instance to register
            priority: Priority level (higher = more priority)
        """
        self._agents[agent.name] = agent
        self._agent_priorities[agent.name] = priority
        logger.info(f"Registered agent: {agent.name} with priority {priority}")
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """
        Get an agent by name.
        
        Args:
            name: Agent name
            
        Returns:
            Agent instance or None if not found
        """
        return self._agents.get(name)
    
    def find_suitable_agents(self, processed_query: ProcessedQuery) -> List[BaseAgent]:
        """
        Find agents that can handle the given query.
        
        Args:
            processed_query: ProcessedQuery object
            
        Returns:
            List of suitable agents, sorted by priority
        """
        suitable_agents = []
        
        for agent in self._agents.values():
            if agent.can_handle(processed_query):
                suitable_agents.append(agent)
        
        # Sort by priority (highest first)
        suitable_agents.sort(
            key=lambda a: self._agent_priorities.get(a.name, 0),
            reverse=True
        )
        
        return suitable_agents
    
    def get_all_agents(self) -> List[BaseAgent]:
        """
        Get all registered agents.
        
        Returns:
            List of all agents
        """
        return list(self._agents.values())
    
    def get_agent_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """
        Get capabilities of all registered agents.
        
        Returns:
            Dictionary mapping agent names to their capabilities
        """
        return {
            name: agent.get_capabilities()
            for name, agent in self._agents.items()
        }

# Global agent registry instance
agent_registry = AgentRegistry()

def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry instance."""
    return agent_registry

