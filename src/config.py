"""
Configuration management for the UBERON agent application.

This module uses Pydantic's BaseSettings to manage configuration from environment
variables with type validation.
"""

import os
import sys
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator, HttpUrl

# Load environment variables from .env file if it exists
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

class UberonApiSettings(BaseModel):
    """Settings specific to the UBERON API."""
    
    BASE_URL: str = Field(
        os.environ.get('UBERON_API_BASE_URL', "https://www.ebi.ac.uk/ols4/api"), 
        description="Base URL for the UBERON ontology API (EBI OLS4)"
    )
    SEARCH_ENDPOINT: str = Field(
        os.environ.get('UBERON_API_SEARCH_ENDPOINT', "/search"),
        description="Endpoint for searching UBERON terms"
    )
    TERM_ENDPOINT: str = Field(
        os.environ.get('UBERON_API_TERM_ENDPOINT', "/terms"),
        description="Endpoint for retrieving specific UBERON terms"
    )
    TIMEOUT: int = Field(
        int(os.environ.get('UBERON_API_TIMEOUT', "30")),
        description="Timeout in seconds for API requests"
    )
    MAX_RETRIES: int = Field(
        int(os.environ.get('UBERON_API_MAX_RETRIES', "3")),
        description="Maximum number of retries for failed requests"
    )
    PARAMS: Dict[str, Any] = Field(
        {"ontology": "uberon"},
        description="Default parameters to include in all requests"
    )

class Settings(BaseModel):
    """Application settings loaded from environment variables."""
    
    # API Keys
    ANTHROPIC_API_KEY: str = Field(
        os.environ.get('ANTHROPIC_API_KEY', None),
        description="Anthropic API key for Claude 3.5"
    )
    
    # LLM Configuration
    MODEL_NAME: str = Field(
        os.environ.get('LLM_MODEL_NAME', "claude-3-5-sonnet-20240620"), 
        description="Claude model version to use"
    )
    MAX_TOKENS: int = Field(
        int(os.environ.get('LLM_MAX_TOKENS', "4000")), 
        description="Maximum number of tokens for LLM responses"
    )
    TEMPERATURE: float = Field(
        float(os.environ.get('LLM_TEMPERATURE', "0.1")), 
        description="Temperature for LLM generation (0.0-1.0)"
    )
    
    # UBERON API Configuration
    UBERON_API: UberonApiSettings = Field(
        default_factory=UberonApiSettings,
        description="UBERON API configuration"
    )
    
    @validator("ANTHROPIC_API_KEY", pre=True)
    def validate_api_key(cls, v):
        if not v:
            raise ValueError("ANTHROPIC_API_KEY is required. Please set your API key in the environment variables.")
        return v
    
    @validator("TEMPERATURE")
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("TEMPERATURE must be between 0.0 and 1.0")
        return v

# Create a global instance of settings
settings = Settings()
