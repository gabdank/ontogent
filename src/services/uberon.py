"""
UBERON service for interacting with the UBERON ontology.

This module handles fetching data from UBERON ontology sources and converting
the raw data into structured UberonTerm objects.
"""

import logging
import json
from typing import List, Dict, Any, Optional
import requests

from src.config import settings
from src.models.uberon import UberonTerm, SearchQuery, SearchResult

# Set up logging
logger = logging.getLogger(__name__)


class UberonService:
    """Service for interacting with the UBERON ontology."""
    
    def __init__(self):
        """Initialize the UBERON service."""
        self.api_url = settings.UBERON_API_URL
        logger.info(f"UBERON service initialized with API URL: {self.api_url}")
    
    def search(self, query: SearchQuery) -> SearchResult:
        """
        Search for UBERON terms matching the query.
        
        Args:
            query: SearchQuery object containing search parameters
            
        Returns:
            SearchResult object containing matching terms
        """
        try:
            logger.info(f"Searching UBERON for: {query.query}")
            
            # In a real implementation, we would make an API call to the UBERON service
            # For now, we'll simulate a response with mock data
            
            # Example of how the API call might look:
            # response = requests.get(
            #     self.api_url,
            #     params={
            #         "q": query.query,
            #         "ontology": "UBERON",
            #         "max_results": query.max_results
            #     }
            # )
            # response.raise_for_status()
            # data = response.json()
            
            # For now, return a mock result
            mock_terms = self._get_mock_results(query.query)
            
            result = SearchResult(
                query=query.query,
                matches=mock_terms,
                total_matches=len(mock_terms),
                best_match=mock_terms[0] if mock_terms else None,
                confidence=0.85 if mock_terms else None,
                reasoning="Based on exact match with the anatomical term name"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error searching UBERON: {e}")
            return SearchResult(query=query.query)
    
    def get_term_by_id(self, term_id: str) -> Optional[UberonTerm]:
        """
        Get a specific UBERON term by ID.
        
        Args:
            term_id: UBERON ID (e.g., 'UBERON:0000948')
            
        Returns:
            UberonTerm object or None if not found
        """
        try:
            logger.info(f"Getting UBERON term by ID: {term_id}")
            
            # In a real implementation, we would query the ontology here
            # For now, return mock data
            
            if term_id == "UBERON:0000948":
                return UberonTerm(
                    id="UBERON:0000948",
                    label="heart",
                    definition="A hollow, muscular organ, which, by contracting rhythmically, keeps up the circulation of the blood.",
                    synonyms=["cardiac muscle"],
                    parent_ids=["UBERON:0000077"],
                    url="http://purl.obolibrary.org/obo/UBERON_0000948"
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting UBERON term by ID: {e}")
            return None
    
    def _get_mock_results(self, query: str) -> List[UberonTerm]:
        """
        Get mock results for testing.
        
        Args:
            query: Search query
            
        Returns:
            List of UberonTerm objects
        """
        # Very basic mock implementation
        mock_data = {
            "heart": [
                UberonTerm(
                    id="UBERON:0000948",
                    label="heart",
                    definition="A hollow, muscular organ, which, by contracting rhythmically, keeps up the circulation of the blood.",
                    synonyms=["cardiac muscle"],
                    parent_ids=["UBERON:0000077"],
                    url="http://purl.obolibrary.org/obo/UBERON_0000948"
                ),
                UberonTerm(
                    id="UBERON:0004146",
                    label="primitive heart",
                    definition="The developing heart at the cardiac crescent stage.",
                    synonyms=["embryonic heart"],
                    parent_ids=["UBERON:0000948"],
                    url="http://purl.obolibrary.org/obo/UBERON_0004146"
                )
            ],
            "liver": [
                UberonTerm(
                    id="UBERON:0002107",
                    label="liver",
                    definition="A large, reddish-brown glandular organ in the abdominal cavity that is responsible for detoxifying metabolites, synthesizing proteins, and producing biochemicals necessary for digestion.",
                    synonyms=["hepar"],
                    parent_ids=["UBERON:0001434"],
                    url="http://purl.obolibrary.org/obo/UBERON_0002107"
                )
            ]
        }
        
        # Very simple matching logic for demo purposes
        for key, terms in mock_data.items():
            if key in query.lower():
                return terms
        
        return [] 