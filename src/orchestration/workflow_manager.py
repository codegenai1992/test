"""
Workflow manager for orchestrating multi-agent interactions using LangGraph.
"""

import time
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from config.settings import get_settings
from ..processing.query_processor import QueryProcessor, ProcessedQuery
from ..agents.base_agent import BaseAgent, AgentResult, get_agent_registry
from ..agents.table_discovery_agent import TableDiscoveryAgent
from ..agents.trend_analysis_agent import TrendAnalysisAgent

logger = logging.getLogger(__name__)

class WorkflowState(Enum):
    """Workflow execution states."""
    INITIALIZED = "initialized"
    PROCESSING = "processing"
    AGENT_SELECTION = "agent_selection"
    AGENT_EXECUTION = "agent_execution"
    RESULT_SYNTHESIS = "result_synthesis"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class WorkflowResult:
    """Result container for workflow execution."""
    success: bool
    final_result: Any
    message: str
    suggestions: List[str]
    execution_path: List[str]
    agent_results: List[AgentResult]
    total_execution_time: float
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'success': self.success,
            'final_result': self.final_result,
            'message': self.message,
            'suggestions': self.suggestions,
            'execution_path': self.execution_path,
            'agent_results': [result.to_dict() for result in self.agent_results],
            'total_execution_time': self.total_execution_time,
            'metadata': self.metadata
        }

class WorkflowManager:
    """
    Manages multi-agent workflows using LangGraph for orchestration.
    """
    
    def __init__(self):
        """Initialize the workflow manager."""
        self.settings = get_settings()
        self.query_processor = QueryProcessor()
        self.agent_registry = get_agent_registry()
        
        # Initialize and register agents
        self._initialize_agents()
        
        # Build the workflow graph
        self.workflow_graph = self._build_workflow_graph()
        
        logger.info("Workflow manager initialized")
    
    def _initialize_agents(self):
        """Initialize and register all available agents."""
        # Register table discovery agent
        table_agent = TableDiscoveryAgent()
        self.agent_registry.register_agent(table_agent, priority=10)
        
        # Register trend analysis agent
        trend_agent = TrendAnalysisAgent()
        self.agent_registry.register_agent(trend_agent, priority=10)
        
        logger.info(f"Registered {len(self.agent_registry.get_all_agents())} agents")
    
    def _build_workflow_graph(self) -> StateGraph:
        """
        Build the LangGraph workflow for agent orchestration.
        
        Returns:
            StateGraph representing the workflow
        """
        # Define the workflow state
        class WorkflowGraphState:
            def __init__(self):
                self.messages: List[BaseMessage] = []
                self.user_query: str = ""
                self.processed_query: Optional[ProcessedQuery] = None
                self.selected_agents: List[BaseAgent] = []
                self.agent_results: List[AgentResult] = []
                self.final_result: Any = None
                self.execution_path: List[str] = []
                self.metadata: Dict[str, Any] = {}
        
        # Create the graph
        workflow = StateGraph(WorkflowGraphState)
        
        # Add nodes
        workflow.add_node("process_query", self._process_query_node)
        workflow.add_node("select_agents", self._select_agents_node)
        workflow.add_node("execute_agents", self._execute_agents_node)
        workflow.add_node("synthesize_results", self._synthesize_results_node)
        
        # Add edges
        workflow.add_edge("process_query", "select_agents")
        workflow.add_edge("select_agents", "execute_agents")
        workflow.add_edge("execute_agents", "synthesize_results")
        workflow.add_edge("synthesize_results", END)
        
        # Set entry point
        workflow.set_entry_point("process_query")
        
        return workflow.compile()
    
    def execute_workflow(self, user_query: str, 
                        conversation_history: Optional[List[Dict[str, str]]] = None) -> WorkflowResult:
        """
        Execute the complete workflow for a user query.
        
        Args:
            user_query: User's input query
            conversation_history: Optional conversation history
            
        Returns:
            WorkflowResult with execution results
        """
        start_time = time.time()
        
        try:
            # Initialize workflow state
            initial_state = {
                'messages': [HumanMessage(content=user_query)],
                'user_query': user_query,
                'processed_query': None,
                'selected_agents': [],
                'agent_results': [],
                'final_result': None,
                'execution_path': [],
                'metadata': {
                    'conversation_history': conversation_history or [],
                    'start_time': start_time
                }
            }
            
            # Execute the workflow
            final_state = self.workflow_graph.invoke(initial_state)
            
            execution_time = time.time() - start_time
            
            # Build the final result
            return WorkflowResult(
                success=True,
                final_result=final_state.get('final_result'),
                message=self._extract_final_message(final_state),
                suggestions=self._extract_suggestions(final_state),
                execution_path=final_state.get('execution_path', []),
                agent_results=final_state.get('agent_results', []),
                total_execution_time=execution_time,
                metadata=final_state.get('metadata', {})
            )
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            
            return WorkflowResult(
                success=False,
                final_result=None,
                message=f"I encountered an error while processing your request: {str(e)}",
                suggestions=[
                    "Try rephrasing your question",
                    "Be more specific about what you're looking for",
                    "Ask for help with available data"
                ],
                execution_path=["error"],
                agent_results=[],
                total_execution_time=time.time() - start_time,
                metadata={'error': str(e)}
            )
    
    def _process_query_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the user query to extract keywords and intent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with processed query
        """
        try:
            user_query = state['user_query']
            processed_query = self.query_processor.process_user_query(user_query)
            
            state['processed_query'] = processed_query
            state['execution_path'].append('query_processing')
            
            logger.info(f"Processed query with intent: {processed_query.intent}")
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            state['metadata']['processing_error'] = str(e)
        
        return state
    
    def _select_agents_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Select appropriate agents based on the processed query.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with selected agents
        """
        try:
            processed_query = state['processed_query']
            
            if not processed_query:
                logger.error("No processed query available for agent selection")
                return state
            
            # Find suitable agents
            suitable_agents = self.agent_registry.find_suitable_agents(processed_query)
            
            if not suitable_agents:
                # Fallback to table discovery agent for general queries
                table_agent = self.agent_registry.get_agent("Table Discovery Agent")
                if table_agent:
                    suitable_agents = [table_agent]
            
            state['selected_agents'] = suitable_agents
            state['execution_path'].append('agent_selection')
            
            agent_names = [agent.name for agent in suitable_agents]
            logger.info(f"Selected agents: {agent_names}")
            
        except Exception as e:
            logger.error(f"Error selecting agents: {e}")
            state['metadata']['selection_error'] = str(e)
        
        return state
    
    def _execute_agents_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the selected agents.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with agent results
        """
        try:
            selected_agents = state['selected_agents']
            processed_query = state['processed_query']
            
            if not selected_agents or not processed_query:
                logger.error("No agents selected or processed query missing")
                return state
            
            agent_results = []
            
            # Execute each selected agent
            for agent in selected_agents:
                try:
                    logger.info(f"Executing agent: {agent.name}")
                    result = agent.execute(processed_query)
                    agent_results.append(result)
                    
                    # Log the execution
                    agent.log_execution(processed_query, result)
                    
                    # If we get a successful result, we might not need to run other agents
                    if result.success and len(agent_results) == 1:
                        break
                        
                except Exception as e:
                    logger.error(f"Error executing agent {agent.name}: {e}")
                    error_result = agent.handle_error(e, processed_query)
                    agent_results.append(error_result)
            
            state['agent_results'] = agent_results
            state['execution_path'].append('agent_execution')
            
        except Exception as e:
            logger.error(f"Error executing agents: {e}")
            state['metadata']['execution_error'] = str(e)
        
        return state
    
    def _synthesize_results_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesize results from multiple agents into a final response.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with synthesized results
        """
        try:
            agent_results = state['agent_results']
            
            if not agent_results:
                state['final_result'] = {
                    'success': False,
                    'message': "No results were generated from the available agents.",
                    'suggestions': ["Try rephrasing your question", "Be more specific about your request"]
                }
                return state
            
            # Find the best result (first successful one, or best unsuccessful one)
            best_result = None
            for result in agent_results:
                if result.success:
                    best_result = result
                    break
            
            if not best_result:
                # No successful results, pick the one with the most helpful message
                best_result = max(agent_results, key=lambda r: len(r.message))
            
            # Combine suggestions from all agents
            all_suggestions = []
            for result in agent_results:
                all_suggestions.extend(result.suggestions)
            
            # Remove duplicates while preserving order
            unique_suggestions = []
            seen = set()
            for suggestion in all_suggestions:
                if suggestion not in seen:
                    seen.add(suggestion)
                    unique_suggestions.append(suggestion)
            
            # Create final result
            state['final_result'] = {
                'success': best_result.success,
                'data': best_result.data,
                'message': best_result.message,
                'suggestions': unique_suggestions[:5],  # Limit to 5 suggestions
                'primary_agent': best_result.agent_name,
                'all_agent_results': [result.to_dict() for result in agent_results]
            }
            
            state['execution_path'].append('result_synthesis')
            
        except Exception as e:
            logger.error(f"Error synthesizing results: {e}")
            state['metadata']['synthesis_error'] = str(e)
            state['final_result'] = {
                'success': False,
                'message': f"Error synthesizing results: {str(e)}",
                'suggestions': ["Try your request again", "Contact support if the problem persists"]
            }
        
        return state
    
    def _extract_final_message(self, final_state: Dict[str, Any]) -> str:
        """Extract the final message from the workflow state."""
        final_result = final_state.get('final_result', {})
        return final_result.get('message', 'No message available')
    
    def _extract_suggestions(self, final_state: Dict[str, Any]) -> List[str]:
        """Extract suggestions from the workflow state."""
        final_result = final_state.get('final_result', {})
        return final_result.get('suggestions', [])
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """
        Get the current status of the workflow manager.
        
        Returns:
            Dictionary with workflow manager status
        """
        agents = self.agent_registry.get_all_agents()
        
        return {
            'total_agents': len(agents),
            'agent_capabilities': self.agent_registry.get_agent_capabilities(),
            'workflow_graph_nodes': list(self.workflow_graph.nodes.keys()) if hasattr(self.workflow_graph, 'nodes') else [],
            'settings': {
                'max_results': self.settings.snowflake.max_retries,
                'timeout': self.settings.cortex_ai.timeout
            }
        }
    
    def test_workflow(self, test_query: str = "Show me tables related to production") -> Dict[str, Any]:
        """
        Test the workflow with a sample query.
        
        Args:
            test_query: Test query to execute
            
        Returns:
            Test results
        """
        try:
            result = self.execute_workflow(test_query)
            
            return {
                'test_successful': result.success,
                'execution_time': result.total_execution_time,
                'agents_executed': len(result.agent_results),
                'execution_path': result.execution_path,
                'message_length': len(result.message),
                'suggestions_count': len(result.suggestions)
            }
            
        except Exception as e:
            return {
                'test_successful': False,
                'error': str(e),
                'execution_time': 0,
                'agents_executed': 0
            }
    
    def add_custom_agent(self, agent: BaseAgent, priority: int = 0):
        """
        Add a custom agent to the workflow.
        
        Args:
            agent: Custom agent instance
            priority: Priority level for the agent
        """
        self.agent_registry.register_agent(agent, priority)
        logger.info(f"Added custom agent: {agent.name}")
    
    def get_conversation_context(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Analyze conversation history to provide context for the workflow.
        
        Args:
            conversation_history: List of conversation exchanges
            
        Returns:
            Context information for the workflow
        """
        if not conversation_history:
            return {}
        
        # Extract patterns from conversation history
        recent_intents = []
        recent_topics = []
        
        for exchange in conversation_history[-5:]:  # Last 5 exchanges
            user_message = exchange.get('user', '')
            if user_message:
                # Quick intent detection
                if any(keyword in user_message.lower() for keyword in ['table', 'show', 'list']):
                    recent_intents.append('table_discovery')
                elif any(keyword in user_message.lower() for keyword in ['trend', 'analysis', 'production']):
                    recent_intents.append('trend_analysis')
                
                # Extract potential topics
                words = user_message.lower().split()
                for word in words:
                    if len(word) > 3 and word not in ['show', 'list', 'find', 'what', 'where', 'when']:
                        recent_topics.append(word)
        
        return {
            'recent_intents': list(set(recent_intents)),
            'recent_topics': list(set(recent_topics)),
            'conversation_length': len(conversation_history),
            'context_available': True
        }

