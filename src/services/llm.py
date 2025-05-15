"""
LLM service for interacting with Claude 3.5 via the Anthropic API.

This module encapsulates the interaction with the Anthropic API to query the
Claude 3.5 model for finding UBERON terms.
"""

import logging
import json
from typing import Dict, Any, Optional, List

import anthropic
from anthropic.types import MessageParam

from src.config import settings

# Set up logging
logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with Claude 3.5 via Anthropic API."""
    
    def __init__(self):
        """Initialize the LLM service with API key from settings."""
        try:
            self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            logger.info("LLM service initialized with Anthropic API")
                
            self.model = settings.MODEL_NAME
            self.max_tokens = settings.MAX_TOKENS
            self.temperature = settings.TEMPERATURE
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {e}")
            raise
    
    def query(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Query the LLM with a prompt.
        
        Args:
            prompt: The user prompt to send to the model
            system_prompt: Optional system prompt for context
            
        Returns:
            The model's response as a string
        """
        try:
            logger.debug(f"Querying LLM with prompt: {prompt[:100]}...")
            
            messages: List[MessageParam] = [
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=messages,
            )
            
            return response.content[0].text
        
        except Exception as e:
            logger.error(f"Error querying LLM: {e}")
            raise
    
    def analyze_uberon_query(self, user_query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a user query to identify relevant UBERON terms.
        
        Args:
            user_query: The user's query about an anatomical structure
            context: Optional additional context
            
        Returns:
            Dict containing the analysis results
        """
        system_prompt = """
        You are an expert in anatomy and the UBERON ontology. Your task is to analyze the user's query about 
        an anatomical structure and identify the most relevant UBERON terms that might match their description.
        
        Focus on extracting:
        1. Key anatomical concepts from the query
        2. Species information if mentioned
        3. Developmental stage if mentioned
        4. Any modifiers or qualifiers that might narrow down the search
        
        Format your response as a JSON object with the following fields:
        - extracted_concepts: List of key anatomical concepts
        - possible_uberon_terms: List of potential UBERON terms that might match
        - recommended_search_query: A suggested search query to find the UBERON term
        - explanation: Brief explanation of your reasoning
        """
        
        prompt = f"Please analyze this query about an anatomical structure: {user_query}"
        if context:
            prompt += f"\n\nAdditional context: {context}"
        
        try:
            response = self.query(prompt, system_prompt)
            return {"raw_response": response}
        except Exception as e:
            logger.error(f"Error analyzing UBERON query: {e}")
            raise 