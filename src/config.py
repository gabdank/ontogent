"""
Configuration management for the UBERON agent application.

This module uses Pydantic's BaseSettings to manage configuration from environment
variables with type validation.
"""

import os
import sys
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator

# Load environment variables from .env file if it exists
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# Determine if we're in development mode
DEV_MODE = os.environ.get('ONTOGENT_DEV_MODE', 'false').lower() in ('true', '1', 't')

class Settings(BaseModel):
    """Application settings loaded from environment variables."""
    
    # API Keys
    ANTHROPIC_API_KEY: str = Field(
        os.environ.get('ANTHROPIC_API_KEY', 'sk-ant-mock-api-key-for-development-only' if DEV_MODE else None),
        description="Anthropic API key for Claude 3.5"
    )
    
    # LLM Configuration
    MODEL_NAME: str = Field("claude-3-5-sonnet-20240620", description="Claude model version to use")
    MAX_TOKENS: int = Field(4000, description="Maximum number of tokens for LLM responses")
    TEMPERATURE: float = Field(0.1, description="Temperature for LLM generation (0.0-1.0)")
    
    # UBERON API Configuration
    UBERON_API_URL: str = Field(
        "http://www.ontobee.org/api/search", 
        description="URL for the UBERON ontology API"
    )
    
    # Development mode
    DEV_MODE: bool = Field(DEV_MODE, description="Whether to run in development mode with mock data")
    
    @validator("ANTHROPIC_API_KEY", pre=True)
    def validate_api_key(cls, v):
        if not v and not DEV_MODE:
            raise ValueError("ANTHROPIC_API_KEY is required in production mode. Set ONTOGENT_DEV_MODE=true to use mock data.")
        return v
    
    @validator("TEMPERATURE")
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("TEMPERATURE must be between 0.0 and 1.0")
        return v

# Create a global instance of settings
settings = Settings()

# Print a warning if using mock API key
if settings.ANTHROPIC_API_KEY.startswith('sk-ant-mock') and DEV_MODE:
    print("\n⚠️ WARNING: Using mock API key in development mode. LLM functionality will be simulated.\n")
    print("To use real LLM functionality, set your ANTHROPIC_API_KEY environment variable or set ONTOGENT_DEV_MODE=false.\n")
