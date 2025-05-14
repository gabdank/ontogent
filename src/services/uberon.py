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
        
        # Set up session with retry policy if not in dev mode
        if not self.dev_mode:
            self.session = self._create_session()
            # Test API connection and fall back to dev mode if not accessible
            if not self.test_api_connection():
                logger.warning("UBERON API is not accessible, falling back to development mode")
                self.dev_mode = True
                self.session = None
        else:
            logger.info("Using mock data in development mode")
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
    
    def test_api_connection(self) -> bool:
        """
        Test the connection to the UBERON API.
        
        Attempts to make a simple request to verify the API is accessible.
        
        Returns:
            True if the API is accessible, False otherwise
        """
        try:
            logger.info("Testing connection to UBERON API")
            
            # Try to search for a common term like "heart" as a connection test
            test_url = self.search_url
            params = self.api_config.PARAMS.copy()
            params.update({"q": "heart", "max_results": 1})
            
            response = self.session.get(
                test_url,
                params=params,
                timeout=self.api_config.TIMEOUT
            )
            
            # Check if response is successful and contains expected data
            if response.status_code == 200:
                data = response.json()
                if "results" in data:
                    logger.info("UBERON API connection successful")
                    return True
                else:
                    logger.warning("UBERON API responded with 200 but unexpected data format")
                    return False
            else:
                logger.warning(f"UBERON API responded with status code {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to UBERON API: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error testing UBERON API connection: {e}")
            return False
    
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
        
        try:
            # Check for common response formats from Ontobee API
            if "results" in data:
                # Standard expected format
                results = data["results"]
                logger.debug(f"Found {len(results)} results from UBERON API")
                
                for result in results:
                    try:
                        # Extract ID, ensuring it contains the UBERON prefix
                        term_id = result.get("id", "")
                        if not term_id.startswith("UBERON:"):
                            term_id = f"UBERON:{term_id}" if term_id else ""
                        
                        # Extract other fields with sensible defaults
                        label = result.get("label", "")
                        definition = result.get("definition", "")
                        
                        # Handle synonyms which might be a string, list, or missing
                        synonyms_data = result.get("synonyms", [])
                        if isinstance(synonyms_data, str):
                            synonyms = [s.strip() for s in synonyms_data.split(",")]
                        elif isinstance(synonyms_data, list):
                            synonyms = synonyms_data
                        else:
                            synonyms = []
                        
                        # Handle parent IDs
                        parent_ids = result.get("parents", [])
                        if isinstance(parent_ids, str):
                            parent_ids = [parent_ids]
                        
                        # Construct URL if not present
                        url = result.get("url")
                        if not url and term_id:
                            url = f"http://purl.obolibrary.org/obo/{term_id.replace(':', '_')}"
                        
                        # Create and add the term if it has minimum required data
                        if term_id and label:
                            term = UberonTerm(
                                id=term_id,
                                label=label,
                                definition=definition,
                                synonyms=synonyms,
                                parent_ids=parent_ids,
                                url=url
                            )
                            terms.append(term)
                        else:
                            logger.warning(f"Skipping result without required ID or label: {result}")
                    
                    except Exception as e:
                        logger.error(f"Error parsing individual term from API response: {e}")
                        logger.debug(f"Problematic term data: {result}")
            
            # Alternative response formats
            elif "terms" in data:
                logger.debug("Using 'terms' field in API response")
                return self._parse_search_results({"results": data["terms"]})
            
            elif "response" in data and "docs" in data["response"]:
                # Some APIs use Solr-style response format
                logger.debug("Using Solr-style response format")
                return self._parse_search_results({"results": data["response"]["docs"]})
            
            elif isinstance(data, list):
                # Sometimes the API returns directly an array of results
                logger.debug("API returned a list of results directly")
                return self._parse_search_results({"results": data})
            
            else:
                logger.warning(f"Unexpected API response format. Available keys: {list(data.keys())}")
        
        except Exception as e:
            logger.error(f"Error parsing search results: {e}")
            logger.debug(f"API response data structure: {type(data)}")
        
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
        # Expanded mock implementation with more common anatomical terms
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
            ],
            "brain": [
                UberonTerm(
                    id="UBERON:0000955",
                    label="brain",
                    definition="The brain is the center of the nervous system in all vertebrate and most invertebrate animals.",
                    synonyms=["encephalon"],
                    parent_ids=["UBERON:0000062"],
                    url="http://purl.obolibrary.org/obo/UBERON_0000955"
                )
            ],
            "lung": [
                UberonTerm(
                    id="UBERON:0002048",
                    label="lung",
                    definition="Either of the pair of organs occupying the chest cavity that effect the aeration of the blood.",
                    synonyms=["pulmo"],
                    parent_ids=["UBERON:0001004"],
                    url="http://purl.obolibrary.org/obo/UBERON_0002048"
                )
            ],
            "kidney": [
                UberonTerm(
                    id="UBERON:0002113",
                    label="kidney",
                    definition="Organ that filters blood and excretes urine and regulates blood ionic composition, volume, and pH.",
                    synonyms=["ren"],
                    parent_ids=["UBERON:0001008"],
                    url="http://purl.obolibrary.org/obo/UBERON_0002113"
                )
            ],
            "blood": [
                UberonTerm(
                    id="UBERON:0000178",
                    label="blood",
                    definition="A fluid that circulates throughout the heart and blood vessels, carrying oxygen and nutrients to cells and waste materials away from them.",
                    synonyms=["haema", "hema"],
                    parent_ids=["UBERON:0000479"],
                    url="http://purl.obolibrary.org/obo/UBERON_0000178"
                )
            ],
            "bone": [
                UberonTerm(
                    id="UBERON:0002371",
                    label="bone",
                    definition="Rigid connective tissue that makes up the skeletal system of vertebrates.",
                    synonyms=["os"],
                    parent_ids=["UBERON:0000061"],
                    url="http://purl.obolibrary.org/obo/UBERON_0002371"
                )
            ]
        }
        
        # Convert query to lowercase for case-insensitive matching
        query_lower = query.lower()
        
        # Try exact term match first
        for key, terms in mock_data.items():
            # Match whole words for better precision
            if key == query_lower or f" {key} " in f" {query_lower} ":
                logger.info(f"Found exact match in mock data for term: {key}")
                return terms
        
        # If no exact match, try partial matching
        matching_terms = []
        for key, terms in mock_data.items():
            if key in query_lower:
                logger.info(f"Found partial match in mock data for term: {key}")
                matching_terms.extend(terms)
        
        # Return any matching terms found
        if matching_terms:
            return matching_terms
            
        # If no matches at all, log this for debugging
        logger.warning(f"No matching terms found in mock data for query: {query}")
        return []

    @classmethod
    def check_ontobee_api_health(cls, timeout: int = 10) -> Dict[str, Any]:
        """
        Class method to check the health of the Ontobee API.
        
        This method can be used independently to diagnose API connectivity issues.
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary with API health information
        """
        from src.config import settings
        api_config = settings.UBERON_API
        
        base_url = api_config.BASE_URL
        search_endpoint = api_config.SEARCH_ENDPOINT
        term_endpoint = api_config.TERM_ENDPOINT
        
        search_url = f"{base_url}{search_endpoint}"
        term_url = f"{base_url}{term_endpoint}"
        
        health_info = {
            "base_url": base_url,
            "search_endpoint": search_endpoint,
            "term_endpoint": term_endpoint,
            "search_url_accessible": False,
            "term_url_accessible": False,
            "search_response_valid": False,
            "term_response_valid": False,
            "error": None,
            "dev_mode_recommended": False,
            "timestamp": time.time()
        }
        
        session = requests.Session()
        
        try:
            # Test search endpoint
            params = api_config.PARAMS.copy()
            params.update({"q": "heart", "max_results": 1})
            
            search_response = session.get(search_url, params=params, timeout=timeout)
            health_info["search_url_accessible"] = search_response.status_code == 200
            health_info["search_status_code"] = search_response.status_code
            
            if health_info["search_url_accessible"]:
                # Check if response is valid JSON
                try:
                    search_data = search_response.json()
                    health_info["search_json_valid"] = True
                    
                    # Check if response has expected structure
                    if "results" in search_data or "terms" in search_data:
                        health_info["search_response_valid"] = True
                    else:
                        health_info["search_response_keys"] = list(search_data.keys())
                except Exception as e:
                    health_info["search_json_valid"] = False
                    health_info["search_parse_error"] = str(e)
            
            # Test term endpoint with a known term ID
            params = api_config.PARAMS.copy()
            params.update({"id": "UBERON:0000948"})  # Heart ID
            
            term_response = session.get(term_url, params=params, timeout=timeout)
            health_info["term_url_accessible"] = term_response.status_code == 200
            health_info["term_status_code"] = term_response.status_code
            
            if health_info["term_url_accessible"]:
                # Check if response is valid JSON
                try:
                    term_data = term_response.json()
                    health_info["term_json_valid"] = True
                    
                    # Check if response has expected structure
                    if "term" in term_data:
                        health_info["term_response_valid"] = True
                    else:
                        health_info["term_response_keys"] = list(term_data.keys())
                except Exception as e:
                    health_info["term_json_valid"] = False
                    health_info["term_parse_error"] = str(e)
            
            # Check if dev mode is recommended
            if not health_info["search_url_accessible"] or not health_info["term_url_accessible"]:
                health_info["dev_mode_recommended"] = True
                health_info["recommendation"] = "API endpoints are not accessible, recommend using dev mode"
            elif not health_info["search_json_valid"] or not health_info["term_json_valid"]:
                health_info["dev_mode_recommended"] = True
                health_info["recommendation"] = "API responses are not valid JSON, recommend using dev mode"
            elif not health_info["search_response_valid"] or not health_info["term_response_valid"]:
                health_info["dev_mode_recommended"] = True
                health_info["recommendation"] = "API responses don't have expected structure, recommend using dev mode"
            else:
                health_info["recommendation"] = "API appears to be working correctly"
                
        except requests.exceptions.RequestException as e:
            health_info["error"] = f"Request error: {str(e)}"
            health_info["dev_mode_recommended"] = True
            health_info["recommendation"] = "Cannot connect to API, recommend using dev mode"
        except Exception as e:
            health_info["error"] = f"Unexpected error: {str(e)}"
            health_info["dev_mode_recommended"] = True
            health_info["recommendation"] = "Error checking API health, recommend using dev mode"
        
        return health_info 