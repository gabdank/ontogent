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
            
            # DEBUG: Print the raw LLM response
            if isinstance(analysis, dict) and "raw_response" in analysis:
                raw_response = analysis["raw_response"]
                logger.debug(f"Raw LLM response: {raw_response}")
                print(f"DEBUG - Raw LLM response: {raw_response[:200]}..." if len(raw_response) > 200 else raw_response)
            else:
                logger.debug(f"Unexpected analysis format: {analysis}")
                print(f"DEBUG - Unexpected analysis format: {analysis}")
            
            # Step 2: Extract a recommended search query from the LLM analysis
            search_query = user_query
            
            try:
                if isinstance(analysis, dict) and "raw_response" in analysis:
                    # Check if the response is valid JSON
                    raw_response = analysis["raw_response"]
                    
                    # Try to clean the response if it's not valid JSON
                    if raw_response:
                        # Look for starting and ending braces of JSON
                        start_idx = raw_response.find('{')
                        end_idx = raw_response.rfind('}')
                        
                        if start_idx >= 0 and end_idx > start_idx:
                            # Extract what appears to be JSON
                            json_part = raw_response[start_idx:end_idx+1]
                            logger.debug(f"Attempting to parse JSON part: {json_part}")
                            print(f"DEBUG - Attempting to parse JSON part: {json_part[:200]}..." if len(json_part) > 200 else json_part)
                            
                            try:
                                analysis_json = json.loads(json_part)
                                logger.debug(f"Successfully parsed JSON from part of response: {analysis_json}")
                                print(f"DEBUG - Successfully parsed JSON from part of response")
                                if "recommended_search_query" in analysis_json:
                                    search_query = analysis_json["recommended_search_query"]
                                    logger.info(f"Using LLM-recommended search query: {search_query}")
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse extracted JSON part: {e}")
                                print(f"DEBUG - Failed to parse extracted JSON part: {e}")
                        else:
                            # Try the original response in case there are no clear JSON indicators
                            try:
                                analysis_json = json.loads(raw_response)
                                logger.debug(f"Successfully parsed JSON from full response")
                                if "recommended_search_query" in analysis_json:
                                    search_query = analysis_json["recommended_search_query"]
                                    logger.info(f"Using LLM-recommended search query: {search_query}")
                            except json.JSONDecodeError as e:
                                logger.warning(f"Could not parse LLM analysis, using original query: {e}")
                                print(f"DEBUG - Could not parse LLM analysis, using original query: {e}")
                    else:
                        logger.warning("Empty response from LLM")
                        print("DEBUG - Empty response from LLM")
            except Exception as e:
                logger.warning(f"Error processing LLM analysis, using original query: {e}")
                print(f"DEBUG - Error processing LLM analysis: {e}")
            
            # Create the search query object with possibly refined query string
            query_obj = SearchQuery(query=search_query)
            
            # Step 3: Search for UBERON terms using the EBI OLS4 API
            search_result = self.uberon_service.search(query_obj)
            
            # Step 4: If we have matches, determine the best match
            if search_result.matches:
                # Try to find an exact match first before consulting the LLM
                exact_match = self._find_exact_match(user_query, search_result.matches)
                if exact_match:
                    search_result.best_match = exact_match["term"]
                    search_result.confidence = exact_match["confidence"]
                    search_result.reasoning = exact_match["reasoning"]
                # If no exact match and we have multiple terms, ask the LLM to rank them
                elif len(search_result.matches) > 1:
                    best_match = self._rank_terms(user_query, search_result.matches)
                    if best_match:
                        search_result.best_match = best_match["term"]
                        search_result.confidence = best_match["confidence"]
                        search_result.reasoning = best_match["reasoning"]
                # If only one match, use it as the best match
                elif len(search_result.matches) == 1:
                    search_result.best_match = search_result.matches[0]
                    search_result.confidence = 0.8
                    search_result.reasoning = f"Only one matching term found for '{user_query}'."
            
            return search_result
            
        except Exception as e:
            logger.error(f"Error finding UBERON term: {e}")
            # Return an empty result in case of error
            return SearchResult(query=user_query)
    
    def _find_exact_match(self, query: str, terms: List[UberonTerm]) -> Optional[Dict[str, Any]]:
        """
        Find an exact match between the query and term labels.
        
        Args:
            query: The original user query
            terms: List of UberonTerm objects to check
            
        Returns:
            Dict with the matching term, confidence, and reasoning, or None if no exact match
        """
        query_terms = [term.strip().lower() for term in query.split()]
        is_compound_query = len(query_terms) > 1
        
        # First try exact matches (query exactly equals label)
        for term in terms:
            if term.label.lower() == query.lower():
                logger.info(f"Found exact label match: {term.id} - {term.label}")
                return {
                    "term": term,
                    "confidence": 0.95,
                    "reasoning": f"This term directly matches the anatomical structure '{query}'."
                }
        
        # Then try to match each word in the query to term labels
        for term in terms:
            label_words = term.label.lower().split()
            # Check if all query terms appear in the label
            if all(q_term in label_words for q_term in query_terms):
                logger.info(f"Found term with all query terms in label: {term.id} - {term.label}")
                return {
                    "term": term,
                    "confidence": 0.9,
                    "reasoning": f"This term contains all words from the query '{query}' in its label."
                }
        
        # For compound queries (more than one word), we should be careful with simple substring matches
        # For such queries, prefer more sophisticated ranking over simple substring matching
        if is_compound_query:
            # Don't return a simple substring match for compound queries
            # This allows the ranking function to handle complex cases like "embryonic heart"
            return None
            
        # For single-word queries, check if the label is a part of the query
        for term in terms:
            if term.label.lower() in query.lower() and len(term.label) > 3:  # Avoid matching very short terms
                # If we have multiple matches, prefer the most specific term
                # A more specific term is one that matches the query exactly or has fewer additional words
                other_matches = [t for t in terms if t.label.lower() in query.lower() and len(t.label) > 3]
                if other_matches:
                    # Sort by specificity (fewer words = more specific)
                    specific_matches = sorted(other_matches, key=lambda t: len(t.label.split()))
                    most_specific = specific_matches[0]
                    
                    logger.info(f"Found most specific term: {most_specific.id} - {most_specific.label}")
                    return {
                        "term": most_specific,
                        "confidence": 0.85,
                        "reasoning": f"The term '{most_specific.label}' is the most specific match for the query '{query}'."
                    }
                    
                logger.info(f"Found term label contained in query: {term.id} - {term.label}")
                return {
                    "term": term,
                    "confidence": 0.85,
                    "reasoning": f"The term directly represents the structure '{term.label}' mentioned in the query '{query}'."
                }
                
        # No exact match found
        return None
    
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
            logger.debug(f"Ranking {len(terms)} terms for query: '{query}'")
            for i, term in enumerate(terms):
                logger.debug(f"Term {i+1}: {term.id} - {term.label}")
            
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
            logger.debug("Sending ranking prompt to LLM")
            response = self.llm_service.query(prompt, system_prompt)
            logger.debug(f"Received LLM response: {response[:100]}...")
            
            # DEBUG: Print the raw ranking response
            print(f"DEBUG - Raw ranking response: {response[:200]}..." if len(response) > 200 else response)
            
            try:
                # Try to parse the JSON response
                try:
                    result = json.loads(response)
                    logger.debug(f"Parsed LLM response: {result}")
                except json.JSONDecodeError:
                    # Try to extract JSON if response contains other text
                    start_idx = response.find('{')
                    end_idx = response.rfind('}')
                    
                    if start_idx >= 0 and end_idx > start_idx:
                        json_part = response[start_idx:end_idx+1]
                        logger.debug(f"Attempting to parse JSON part: {json_part}")
                        print(f"DEBUG - Attempting to parse JSON part from ranking: {json_part[:200]}..." if len(json_part) > 200 else json_part)
                        result = json.loads(json_part)
                        logger.debug(f"Successfully parsed JSON from part of ranking response: {result}")
                    else:
                        logger.warning("Could not extract JSON from ranking response")
                        print(f"DEBUG - Could not extract JSON from ranking response")
                        raise
                
                # Find the term with the matching ID
                best_match_id = result.get("best_match_id")
                logger.debug(f"Looking for term with ID: {best_match_id}")
                
                matched_term = None
                for term in terms:
                    logger.debug(f"Comparing with term: {term.id}")
                    if term.id == best_match_id:
                        matched_term = term
                        logger.debug(f"Found matching term: {term.id} - {term.label}")
                        break
                
                if matched_term:
                    return {
                        "term": matched_term,
                        "confidence": result.get("confidence", 0.7),
                        "reasoning": result.get("reasoning", "This term best matches the query according to semantic analysis.")
                    }
                
                # If we can't find the exact ID, check if the query matches any term labels
                query_lower = query.lower()
                for term in terms:
                    if term.label.lower() == query_lower:
                        logger.debug(f"Found term with matching label: {term.id} - {term.label}")
                        return {
                            "term": term,
                            "confidence": 0.9,
                            "reasoning": f"This term exactly matches the query '{query}'."
                        }
                
                # If no exact match, just use the first term
                logger.warning(f"Could not find term with ID {best_match_id}, using first term: {terms[0].id} - {terms[0].label}")
                return {
                    "term": terms[0],
                    "confidence": result.get("confidence", 0.7),
                    "reasoning": result.get("reasoning", "This term best matches the query according to semantic analysis.")
                }
                
            except (json.JSONDecodeError, AttributeError, KeyError) as e:
                logger.warning(f"Could not parse LLM ranking response: {e}")
                print(f"DEBUG - Could not parse LLM ranking response: {e}")
                # Fallback to using the first term
                logger.debug(f"Using first term as fallback: {terms[0].id} - {terms[0].label}")
                return {
                    "term": terms[0],
                    "confidence": 0.7,
                    "reasoning": "This term appears to be the most relevant match based on the query."
                }
            
        except Exception as e:
            logger.error(f"Error ranking UBERON terms: {e}")
            print(f"DEBUG - Error ranking UBERON terms: {e}")
            return None 