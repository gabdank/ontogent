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
            self.dev_mode = settings.DEV_MODE
            
            if not self.dev_mode:
                self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                logger.info(f"LLM service initialized with real Anthropic API")
            else:
                self.client = None
                logger.info("LLM service initialized in development mode with mock responses")
                
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
            
            # If in development mode, return mock responses
            if self.dev_mode:
                logger.info("Using mock LLM response in development mode")
                return self._mock_query_response(prompt, system_prompt)
            
            # Otherwise, use the real Anthropic API
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
            
            # If in development mode, we'll just return the mock response
            if self.dev_mode:
                return {"raw_response": response}
            
            # In a real implementation, we would parse the JSON response here
            # For now, we're just returning the raw response
            return {"raw_response": response}
        except Exception as e:
            logger.error(f"Error analyzing UBERON query: {e}")
            raise
    
    def _mock_query_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate a mock response for development mode.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            
        Returns:
            A mock response string
        """
        # Check if this is an analyze_uberon_query call
        if "Please analyze this query about an anatomical structure:" in prompt:
            # Extract the query
            query = prompt.split("Please analyze this query about an anatomical structure:")[1].strip()
            logger.debug(f"Generating mock response for anatomical query: {query}")
            
            # Generate a mock response based on common anatomical terms
            mock_responses = {
                "heart": {
                    "extracted_concepts": ["heart"],
                    "possible_uberon_terms": ["heart", "cardiac muscle tissue"],
                    "recommended_search_query": "heart",
                    "explanation": "The query directly mentions the heart, which is a well-defined anatomical structure."
                },
                "liver": {
                    "extracted_concepts": ["liver"],
                    "possible_uberon_terms": ["liver", "hepatic tissue"],
                    "recommended_search_query": "liver",
                    "explanation": "The query directly mentions the liver, which is a well-defined anatomical structure."
                },
                "embryonic heart": {
                    "extracted_concepts": ["embryonic heart", "embryo", "heart"],
                    "possible_uberon_terms": ["primitive heart", "embryonic heart tube"],
                    "recommended_search_query": "embryonic heart OR primitive heart OR heart primordium",
                    "explanation": "The query mentions an embryonic stage of heart development."
                },
                "colon": {
                    "extracted_concepts": ["colon"],
                    "possible_uberon_terms": ["colon", "large intestine"],
                    "recommended_search_query": "colon",
                    "explanation": "The query directly mentions the colon, which is a well-defined part of the large intestine."
                },
                "brain": {
                    "extracted_concepts": ["brain"],
                    "possible_uberon_terms": ["brain", "encephalon"],
                    "recommended_search_query": "brain",
                    "explanation": "The query directly mentions the brain, which is a well-defined anatomical structure."
                },
                "kidney": {
                    "extracted_concepts": ["kidney"],
                    "possible_uberon_terms": ["kidney", "renal organ"],
                    "recommended_search_query": "kidney",
                    "explanation": "The query directly mentions the kidney, which is a well-defined anatomical structure."
                },
                "lung": {
                    "extracted_concepts": ["lung"],
                    "possible_uberon_terms": ["lung", "pulmonary organ"],
                    "recommended_search_query": "lung",
                    "explanation": "The query directly mentions the lung, which is a well-defined anatomical structure."
                },
                "mouse": {
                    "extracted_concepts": ["mouse", "liver"],
                    "possible_uberon_terms": ["liver", "mouse liver"],
                    "recommended_search_query": "liver Mus musculus",
                    "explanation": "The query mentions a mouse liver, which would correspond to the liver in Mus musculus."
                }
            }
            
            # Find the best matching mock response
            query_lower = query.lower()
            for key, response in mock_responses.items():
                if key in query_lower:
                    logger.debug(f"Found matching mock response for '{key}'")
                    return json.dumps(response, indent=2)
            
            # Default mock response
            logger.debug(f"Using default mock response for '{query}'")
            default_response = {
                "extracted_concepts": [query],
                "possible_uberon_terms": [query],
                "recommended_search_query": query,
                "explanation": f"The query mentions {query}, which might correspond to an anatomical structure."
            }
            return json.dumps(default_response, indent=2)
        
        # For ranking terms, return a generic ranking response
        elif "Please identify the best matching term based on the user's query" in prompt:
            # Extract the query to customize the response a bit
            query_match = "User query: "
            if query_match in prompt:
                query_text = prompt.split(query_match)[1].split("\n")[0].strip()
                logger.debug(f"Generating mock ranking response for query: {query_text}")
                
                # Extract all terms from the prompt
                term_info = []
                current_term = {}
                for line in prompt.split("\n"):
                    if line.startswith("ID: "):
                        if current_term and "id" in current_term:
                            term_info.append(current_term)
                            current_term = {}
                        current_term["id"] = line.split("ID: ")[1].strip()
                    elif line.startswith("Label: ") and "id" in current_term:
                        current_term["label"] = line.split("Label: ")[1].strip()
                    elif line.startswith("Definition: ") and "id" in current_term:
                        current_term["definition"] = line.split("Definition: ")[1].strip()
                
                # Add the last term if it exists
                if current_term and "id" in current_term:
                    term_info.append(current_term)
                
                # Find the best matching term based on the query
                best_match_id = None
                if term_info:
                    # First, look for exact matches with the label
                    query_lower = query_text.lower()
                    for term in term_info:
                        if "label" in term and term["label"].lower() == query_lower:
                            best_match_id = term["id"]
                            logger.debug(f"Found exact label match: {best_match_id}")
                            break
                    
                    # If no exact match, look for terms containing the query
                    if not best_match_id:
                        for term in term_info:
                            if "label" in term and query_lower in term["label"].lower():
                                best_match_id = term["id"]
                                logger.debug(f"Found partial label match: {best_match_id}")
                                break
                    
                    # If still no match, use the first term
                    if not best_match_id:
                        best_match_id = term_info[0]["id"]
                        logger.debug(f"Using first term as fallback: {best_match_id}")
                else:
                    best_match_id = "UBERON:0000948"  # Default to heart
                    logger.debug(f"No terms found, using default: {best_match_id}")
            else:
                best_match_id = "UBERON:0000948"  # Default to heart
                query_text = "anatomical structure"
                logger.debug(f"No query found, using default: {best_match_id}")
            
            # Generate a reasoning based on the query
            reasoning = f"This term most closely matches the {query_text} described in the query based on semantic analysis."
            
            logger.debug(f"Using {best_match_id} as best match for ranking")
            response = {
                "best_match_id": best_match_id,
                "confidence": 0.95,
                "reasoning": reasoning
            }
            return json.dumps(response, indent=2)
        
        # Default mock response as JSON to prevent parsing errors
        logger.debug("Using default mock response for unrecognized prompt")
        return json.dumps({
            "response": "This is a mock response from the LLM service in development mode.",
            "status": "ok"
        }) 