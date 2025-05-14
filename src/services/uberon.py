"""
UBERON service for interacting with the UBERON ontology.

This module handles fetching data from UBERON ontology sources and converting
the raw data into structured UberonTerm objects.
"""

# NOTE: This file has been modified to handle UBERON API connectivity issues.
# The original version can be found in the same directory with a .bak extension.

import logging
import json
import time
from typing import List, Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config import settings
from src.models.uberon import UberonTerm, SearchQuery, SearchResult
from src.utils.logging_utils import log_exceptions

# Set up logging
logger = logging.getLogger(__name__)

# Create a decorator instance with our logger
log_with_context = log_exceptions(logger)


class UberonService:
    """Service for interacting with the UBERON ontology."""
    
    def __init__(self):
        """Initialize the UBERON service with configured retry policy."""
        # Force dev mode to true temporarily until API issues are resolved
        self.dev_mode = settings.DEV_MODE
        
        self.api_config = settings.UBERON_API
        
        # Construct API URLs
        self.search_url = f"{self.api_config.BASE_URL}{self.api_config.SEARCH_ENDPOINT}"
        self.term_url = f"{self.api_config.BASE_URL}{self.api_config.TERM_ENDPOINT}"
        
        logger.info(f"UBERON service initialized with API URL: {self.search_url}")
        logger.info(f"Using mock data due to UBERON API connectivity issues")
        
        # Set up session with retry policy if not in dev mode
        if not self.dev_mode:
            self.session = self._create_session()
        else:
            self.session = None
    
    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry configuration.
        
        Returns:
            Configured requests.Session object
        """
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.api_config.MAX_RETRIES,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    @log_with_context
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
            
            # Use mock data in development mode
            if self.dev_mode:
                logger.info("Using mock data in development mode")
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
            
            # Make the actual API call in production mode
            params = self.api_config.PARAMS.copy()
            params.update({
                "q": query.query,
                "max_results": query.max_results
            })
            
            logger.debug(f"Sending UBERON API request to {self.search_url} with params: {params}")
            
            response = self.session.get(
                self.search_url,
                params=params,
                timeout=self.api_config.TIMEOUT
            )
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            logger.debug(f"Received UBERON API response with status code {response.status_code}")
            
            # Convert API response to UberonTerm objects
            terms = self._parse_search_results(data)
            
            result = SearchResult(
                query=query.query,
                matches=terms,
                total_matches=len(terms),
                best_match=terms[0] if terms else None,
                confidence=0.9 if terms else None,
                reasoning="Based on API search results"
            )
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error in UBERON API request: {e}")
            return SearchResult(query=query.query)
        except Exception as e:
            logger.error(f"Error searching UBERON: {e}")
            return SearchResult(query=query.query)
    
    @log_with_context
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
            
            # Use mock data in development mode
            if self.dev_mode:
                # Return mock data for known terms
                if term_id == "UBERON:0000948":
                    return UberonTerm(
                        id="UBERON:0000948",
                        label="heart",
                        definition="A hollow, muscular organ, which, by contracting rhythmically, keeps up the circulation of the blood.",
                        synonyms=["cardiac muscle"],
                        parent_ids=["UBERON:0000077"],
                        url="http://purl.obolibrary.org/obo/UBERON_0000948"
                    )
                elif term_id == "UBERON:0004146":
                    return UberonTerm(
                        id="UBERON:0004146",
                        label="primitive heart",
                        definition="The developing heart at the cardiac crescent stage.",
                        synonyms=["embryonic heart"],
                        parent_ids=["UBERON:0000948"],
                        url="http://purl.obolibrary.org/obo/UBERON_0004146"
                    )
                elif term_id == "UBERON:0002107":
                    return UberonTerm(
                        id="UBERON:0002107",
                        label="liver",
                        definition="A large, reddish-brown glandular organ in the abdominal cavity that is responsible for detoxifying metabolites, synthesizing proteins, and producing biochemicals necessary for digestion.",
                        synonyms=["hepar"],
                        parent_ids=["UBERON:0001434"],
                        url="http://purl.obolibrary.org/obo/UBERON_0002107"
                    )
                return None
            
            # Make the actual API call in production mode
            params = self.api_config.PARAMS.copy()
            params.update({
                "id": term_id
            })
            
            response = self.session.get(
                self.term_url,
                params=params,
                timeout=self.api_config.TIMEOUT
            )
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            
            # Convert API response to UberonTerm object
            return self._parse_term_result(data)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error in UBERON API request: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting UBERON term by ID: {e}")
            return None
    
    def _parse_search_results(self, data: Dict[str, Any]) -> List[UberonTerm]:
        """
        Parse search results from the UBERON API.
        
        Args:
            data: JSON response from the API
            
        Returns:
            List of UberonTerm objects
        """
        terms = []
        
        # This parsing logic should be updated based on the actual UBERON API response format
        # The following is a placeholder implementation
        if "results" in data:
            for result in data["results"]:
                try:
                    term = UberonTerm(
                        id=result.get("id", ""),
                        label=result.get("label", ""),
                        definition=result.get("definition", ""),
                        synonyms=result.get("synonyms", []),
                        parent_ids=result.get("parents", []),
                        url=result.get("url", f"http://purl.obolibrary.org/obo/{result.get('id', '').replace(':', '_')}")
                    )
                    terms.append(term)
                except Exception as e:
                    logger.error(f"Error parsing term from API response: {e}")
        
        return terms
    
    def _parse_term_result(self, data: Dict[str, Any]) -> Optional[UberonTerm]:
        """
        Parse a single term result from the UBERON API.
        
        Args:
            data: JSON response from the API
            
        Returns:
            UberonTerm object or None if parsing fails
        """
        # This parsing logic should be updated based on the actual UBERON API response format
        # The following is a placeholder implementation
        try:
            if "term" in data:
                term_data = data["term"]
                return UberonTerm(
                    id=term_data.get("id", ""),
                    label=term_data.get("label", ""),
                    definition=term_data.get("definition", ""),
                    synonyms=term_data.get("synonyms", []),
                    parent_ids=term_data.get("parents", []),
                    url=term_data.get("url", f"http://purl.obolibrary.org/obo/{term_data.get('id', '').replace(':', '_')}")
                )
            return None
        except Exception as e:
            logger.error(f"Error parsing term result: {e}")
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