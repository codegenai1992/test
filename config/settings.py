"""
Configuration management module for Snowflake AI Assistant.
Handles loading and validation of configuration from environment variables and YAML files.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseSettings, Field, validator
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class SnowflakeConfig(BaseSettings):
    """Snowflake database configuration."""
    
    account: str = Field(..., env="SNOWFLAKE_ACCOUNT")
    user: str = Field(..., env="SNOWFLAKE_USER")
    password: str = Field(..., env="SNOWFLAKE_PASSWORD")
    warehouse: str = Field(..., env="SNOWFLAKE_WAREHOUSE")
    database: str = Field(..., env="SNOWFLAKE_DATABASE")
    schema: str = Field(..., env="SNOWFLAKE_SCHEMA")
    role: Optional[str] = Field(None, env="SNOWFLAKE_ROLE")
    
    connection_timeout: int = 30
    query_timeout: int = 300
    max_retries: int = 3
    pool_size: int = 5

class CortexAIConfig(BaseSettings):
    """Snowflake Cortex AI configuration."""
    
    model: str = Field("claude-4-sonnet", env="CORTEX_AI_MODEL")
    endpoint: Optional[str] = Field(None, env="CORTEX_AI_ENDPOINT")
    max_tokens: int = 4000
    temperature: float = 0.1
    timeout: int = 60
    max_retries: int = 3

class AppConfig(BaseSettings):
    """Main application configuration."""
    
    name: str = Field("Snowflake AI Assistant", env="APP_NAME")
    version: str = Field("1.0.0", env="APP_VERSION")
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

class LangChainConfig(BaseSettings):
    """LangChain and LangGraph configuration."""
    
    tracing_v2: bool = Field(False, env="LANGCHAIN_TRACING_V2")
    endpoint: Optional[str] = Field(None, env="LANGCHAIN_ENDPOINT")
    api_key: Optional[str] = Field(None, env="LANGCHAIN_API_KEY")
    project: str = Field("snowflake-ai-assistant", env="LANGCHAIN_PROJECT")

class StreamlitConfig(BaseSettings):
    """Streamlit application configuration."""
    
    server_port: int = Field(8501, env="STREAMLIT_SERVER_PORT")
    server_address: str = Field("0.0.0.0", env="STREAMLIT_SERVER_ADDRESS")

class Settings:
    """Main settings class that combines all configuration."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize settings with optional config file path."""
        self.config_path = config_path or self._get_default_config_path()
        self._load_yaml_config()
        self._load_pydantic_configs()
    
    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        current_dir = Path(__file__).parent
        return str(current_dir / "config.yaml")
    
    def _load_yaml_config(self):
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as file:
                self.yaml_config = yaml.safe_load(file)
        except FileNotFoundError:
            print(f"Warning: Config file {self.config_path} not found. Using defaults.")
            self.yaml_config = {}
        except yaml.YAMLError as e:
            print(f"Error parsing YAML config: {e}")
            self.yaml_config = {}
    
    def _load_pydantic_configs(self):
        """Load and validate Pydantic configuration models."""
        self.app = AppConfig()
        self.snowflake = SnowflakeConfig()
        self.cortex_ai = CortexAIConfig()
        self.langchain = LangChainConfig()
        self.streamlit = StreamlitConfig()
        
        # Update with YAML config values
        self._update_from_yaml()
    
    def _update_from_yaml(self):
        """Update configuration with values from YAML file."""
        if not self.yaml_config:
            return
        
        # Update Snowflake config
        if "snowflake" in self.yaml_config:
            sf_config = self.yaml_config["snowflake"]
            for key, value in sf_config.items():
                if hasattr(self.snowflake, key):
                    setattr(self.snowflake, key, value)
        
        # Update Cortex AI config
        if "cortex_ai" in self.yaml_config:
            ai_config = self.yaml_config["cortex_ai"]
            for key, value in ai_config.items():
                if hasattr(self.cortex_ai, key):
                    setattr(self.cortex_ai, key, value)
        
        # Update App config
        if "app" in self.yaml_config:
            app_config = self.yaml_config["app"]
            for key, value in app_config.items():
                if hasattr(self.app, key):
                    setattr(self.app, key, value)
    
    def get_snowflake_connection_params(self) -> Dict[str, Any]:
        """Get Snowflake connection parameters as dictionary."""
        return {
            "account": self.snowflake.account,
            "user": self.snowflake.user,
            "password": self.snowflake.password,
            "warehouse": self.snowflake.warehouse,
            "database": self.snowflake.database,
            "schema": self.snowflake.schema,
            "role": self.snowflake.role,
        }
    
    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Get configuration for a specific agent."""
        agents_config = self.yaml_config.get("agents", {})
        return agents_config.get(agent_name, {})
    
    def get_processing_config(self) -> Dict[str, Any]:
        """Get processing configuration."""
        return self.yaml_config.get("processing", {})
    
    def get_ui_config(self) -> Dict[str, Any]:
        """Get UI configuration."""
        return self.yaml_config.get("ui", {})

# Global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings

def reload_settings(config_path: Optional[str] = None) -> Settings:
    """Reload settings with optional new config path."""
    global settings
    settings = Settings(config_path)
    return settings

