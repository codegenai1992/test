"""
AI integration module for Snowflake Cortex AI and other AI services.

This module provides integration with Snowflake Cortex AI (Claude 4 Sonnet)
and other AI services for intelligent query processing and response generation.
"""

from .cortex_client import CortexAIClient
from .prompt_templates import PromptTemplates
from .response_parser import ResponseParser

__all__ = [
    "CortexAIClient",
    "PromptTemplates",
    "ResponseParser",
]

