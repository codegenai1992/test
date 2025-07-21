"""
Multi-agent system using LangGraph and LangChain for orchestrated data processing.

This module provides a flexible agent architecture for handling different types
of data queries and analysis tasks through specialized agents.
"""

from .base_agent import BaseAgent, AgentResult
from .table_discovery_agent import TableDiscoveryAgent
from .trend_analysis_agent import TrendAnalysisAgent

__all__ = [
    "BaseAgent",
    "AgentResult",
    "TableDiscoveryAgent",
    "TrendAnalysisAgent",
]

