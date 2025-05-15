"""
UBERON Agent service that integrates LLM and UBERON services to find suitable UBERON terms.

This module contains the main UberonAgent class that coordinates between
the LLM for query understanding and the UBERON service for term retrieval.
"""

import logging
import json
from typing import Dict, Any, List, Optional

from src.services.llm import LLMService
from src.services.uberon import UberonService
from src.models.uberon import SearchQuery, SearchResult, UberonTerm

# Set up logging
logger = logging.getLogger(__name__)


class UberonAgent:
    """
    Agent for finding suitable UBERON terms based on user descriptions.
    
    This agent coordinates between the LLM service for understanding user queries
    and the UBERON service for retrieving and ranking UBERON terms.
    """
    
    def __init__(self):
        """Initialize the UBERON agent with LLM and UBERON services."""
        try:
            self.llm_service = LLMService()
            self.uberon_service = UberonService()
            logger.info("UBERON agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize UBERON agent: {e}")
            raise
    
    def find_term(self, user_query: str) -> SearchResult:
        """
        Find the most suitable UBERON term based on a user query.
        
        Args:
            user_query: The user's description of an anatomical structure
            
        Returns:
            SearchResult with the best matching UBERON term and explanation
        """
        try:
            logger.info(f"Finding UBERON term for query: {user_query}")
            
            # Step 1: Analyze the user query with the LLM
            analysis = self.llm_service.analyze_uberon_query(user_query)
            
            # Step 2: Extract a recommended search query from the LLM analysis
            # In a real implementation, we would parse the JSON response from the LLM
            search_query = user_query
            
            try:
                if isinstance(analysis, dict) and "raw_response" in analysis:
                    analysis_json = json.loads(analysis["raw_response"])
                    if "recommended_search_query" in analysis_json:
                        search_query = analysis_json["recommended_search_query"]
                        logger.info(f"Using LLM-recommended search query: {search_query}")
            except Exception as e:
                logger.warning(f"Could not parse LLM analysis, using original query: {e}")
            
            # Create the search query object with possibly refined query string
            query_obj = SearchQuery(query=search_query)
            
            # Step 3: Search for UBERON terms using the EBI OLS4 API
            search_result = self.uberon_service.search(query_obj)
            
            # Step 4: If we have multiple matches, ask the LLM to rank them
            if len(search_result.matches) > 1:
                best_match = self._rank_terms(user_query, search_result.matches)
                if best_match:
                    search_result.best_match = best_match["term"]
                    search_result.confidence = best_match["confidence"]
                    search_result.reasoning = best_match["reasoning"]
            
            return search_result
            
        except Exception as e:
            logger.error(f"Error finding UBERON term: {e}")
            # Return an empty result in case of error
            return SearchResult(query=user_query)
    
    def _rank_terms(self, query: str, terms: List[UberonTerm]) -> Optional[Dict[str, Any]]:
        """
        Rank UBERON terms based on relevance to the query using the LLM.
        
        Args:
            query: The original user query
            terms: List of UberonTerm objects to rank
            
        Returns:
            Dict with the best matching term, confidence, and reasoning
        """
        try:
            # Create a prompt for the LLM to rank the terms
            system_prompt = """
            You are an expert in anatomy and the UBERON ontology. Your task is to identify the most suitable
            UBERON term for the user's description of an anatomical structure.
            
            I will provide you with:
            1. The user's original query
            2. A list of potential UBERON terms with their IDs, labels, and definitions
            
            Please analyze which term best matches the user's description. Consider factors like:
            - Exact term matches
            - Semantic similarity
            - Specificity (more specific terms are better than general ones if appropriate)
            - Context from the user query (species, developmental stage, etc.)
            
            Format your response as a JSON object with the following fields:
            - best_match_id: The ID of the best matching UBERON term
            - confidence: A number between 0 and 1 indicating your confidence
            - reasoning: A brief explanation of why you chose this term
            """
            
            # Format the terms for the prompt
            terms_text = "\n\n".join([
                f"ID: {term.id}\nLabel: {term.label}\nDefinition: {term.definition or 'N/A'}"
                for term in terms
            ])
            
            prompt = f"""
            User query: {query}
            
            Potential UBERON terms:
            {terms_text}
            
            Please identify the best matching term based on the user's query.
            """
            
            # Query the LLM
            response = self.llm_service.query(prompt, system_prompt)
            
            try:
                # Try to parse the JSON response
                result = json.loads(response)
                
                # Find the term with the matching ID
                for term in terms:
                    if term.id == result.get("best_match_id"):
                        return {
                            "term": term,
                            "confidence": result.get("confidence", 0.7),
                            "reasoning": result.get("reasoning", "This term best matches the query according to semantic analysis.")
                        }
                
                # If we can't find the exact ID, just use the first term
                logger.warning(f"Could not find term with ID {result.get('best_match_id')}, using first term")
                return {
                    "term": terms[0],
                    "confidence": result.get("confidence", 0.7),
                    "reasoning": result.get("reasoning", "This term best matches the query according to semantic analysis.")
                }
                
            except (json.JSONDecodeError, AttributeError, KeyError) as e:
                logger.warning(f"Could not parse LLM ranking response: {e}")
                # Fallback to using the first term
                return {
                    "term": terms[0],
                    "confidence": 0.7,
                    "reasoning": "This term appears to be the most relevant match based on the query."
                }
            
        except Exception as e:
            logger.error(f"Error ranking UBERON terms: {e}")
            return None 