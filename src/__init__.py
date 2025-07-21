"""
Snowflake AI Assistant - A modular application for intelligent data querying and analysis.

This package provides a comprehensive solution for interacting with Snowflake databases
using AI-powered agents orchestrated through LangGraph and LangChain.
"""

__version__ = "1.0.0"
__author__ = "Snowflake AI Assistant Team"
__description__ = "Intelligent Snowflake data assistant with multi-agent orchestration"

# Import main components for easy access
from .services.app_service import AppService
from .database.snowflake_client import SnowflakeClient
from .orchestration.workflow_manager import WorkflowManager

__all__ = [
    "AppService",
    "SnowflakeClient", 
    "WorkflowManager",
]

