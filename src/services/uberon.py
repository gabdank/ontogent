"""
UBERON service for interacting with the UBERON ontology.

This module handles fetching data from UBERON ontology sources using the EBI OLS4 API
and converting the raw data into structured UberonTerm objects.
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
import urllib.parse

from src.config import settings
from src.models.uberon import UberonTerm, SearchQuery, SearchResult
from src.utils.logging_utils import log_exceptions

# Set up logging
logger = logging.getLogger(__name__)

# Create a decorator instance with our logger
log_with_context = log_exceptions(logger)


class UberonService:
    """Service for interacting with the UBERON ontology via EBI OLS4 API."""
    
    def __init__(self):
        """Initialize the UBERON service with configured retry policy."""
        # Use the dev_mode setting from configuration
        self.dev_mode = settings.DEV_MODE
        
        self.api_config = settings.UBERON_API
        
        # Construct API URLs
        self.search_url = f"{self.api_config.BASE_URL}{self.api_config.SEARCH_ENDPOINT}"
        self.term_url = f"{self.api_config.BASE_URL}{self.api_config.TERM_ENDPOINT}"
        
        logger.info(f"UBERON service initialized with API URL: {self.api_config.BASE_URL}")
        
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
        Test the connection to the EBI OLS4 API.
        
        Attempts to make a simple request to verify the API is accessible.
        
        Returns:
            True if the API is accessible, False otherwise
        """
        try:
            logger.info("Testing connection to EBI OLS4 API")
            
            # Try to search for a common term like "heart" as a connection test
            test_url = self.search_url
            params = {
                "q": "heart",
                "ontology": "uberon",
                "rows": 1
            }
            
            response = self.session.get(
                test_url,
                params=params,
                timeout=self.api_config.TIMEOUT
            )
            
            # Check if response is successful and contains expected data
            if response.status_code == 200:
                data = response.json()
                if "response" in data and "docs" in data["response"]:
                    logger.info("EBI OLS4 API connection successful")
                    return True
                else:
                    logger.warning("EBI OLS4 API responded with 200 but unexpected data format")
                    return False
            else:
                logger.warning(f"EBI OLS4 API responded with status code {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to EBI OLS4 API: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error testing EBI OLS4 API connection: {e}")
            return False
    
    @log_with_context
    def search(self, query: SearchQuery) -> SearchResult:
        """
        Search for UBERON terms matching the query using the EBI OLS4 API.
        
        Args:
            query: SearchQuery object containing search parameters
            
        Returns:
            SearchResult object containing matching terms
        """
        try:
            logger.info(f"Searching UBERON for: {query.query} (dev_mode: {self.dev_mode})")
            
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
            params = {
                "q": query.query,
                "ontology": "uberon",
                "rows": query.max_results,
                "queryFields": "label,synonym,description",
                "exact": "false"
            }
            
            logger.debug(f"Sending EBI OLS4 API request to {self.search_url} with params: {params}")
            
            try:
                response = self.session.get(
                    self.search_url,
                    params=params,
                    timeout=self.api_config.TIMEOUT
                )
                response.raise_for_status()
                
                # Parse the response
                data = response.json()
                logger.debug(f"Received EBI OLS4 API response with status code {response.status_code}")
                logger.debug(f"Response structure: {list(data.keys())}")
                
                if "response" in data:
                    logger.debug(f"Found {data['response'].get('numFound', 0)} results in response")
                    if "docs" in data["response"]:
                        logger.debug(f"First 3 docs: {data['response']['docs'][:3]}")
                
                # Convert API response to UberonTerm objects
                terms = self._parse_search_results(data)
                logger.debug(f"Parsed {len(terms)} terms from the API response")
                
                result = SearchResult(
                    query=query.query,
                    matches=terms,
                    total_matches=len(terms) if terms else 0,
                    best_match=terms[0] if terms else None,
                    confidence=0.9 if terms else None,
                    reasoning="Based on EBI OLS4 API search results"
                )
                
                return result
            except requests.exceptions.RequestException as e:
                logger.error(f"Error in EBI OLS4 API request: {e}")
                return SearchResult(query=query.query)
                
        except Exception as e:
            logger.error(f"Error searching UBERON via EBI OLS4 API: {e}")
            import traceback
            logger.debug(f"Exception traceback: {traceback.format_exc()}")
            return SearchResult(query=query.query)
    
    @log_with_context
    def get_term_by_id(self, term_id: str) -> Optional[UberonTerm]:
        """
        Get a specific UBERON term by ID using the EBI OLS4 API.
        
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
            
            # Format term ID for the EBI OLS4 API
            if ":" in term_id:
                formatted_id = term_id.replace(":", "_")
            else:
                formatted_id = term_id
            
            # Construct the IRI for the term (required by EBI OLS4 API)
            term_iri = f"http://purl.obolibrary.org/obo/{formatted_id}"
            # URL encode the IRI 
            encoded_iri = urllib.parse.quote(term_iri)
            
            # Make the API call in production mode
            # In EBI OLS4, the correct URL format is /api/ontologies/uberon/terms/{encoded_iri}
            term_request_url = f"{self.api_config.BASE_URL}/ontologies/uberon/terms/{encoded_iri}"
            
            logger.debug(f"Requesting term details from: {term_request_url}")
            response = self.session.get(
                term_request_url,
                timeout=self.api_config.TIMEOUT
            )
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            
            # Convert API response to UberonTerm object
            return self._parse_term_result(data)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error in EBI OLS4 API request: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting UBERON term by ID: {e}")
            return None
    
    def _parse_search_results(self, data: Dict[str, Any]) -> List[UberonTerm]:
        """
        Parse search results from the EBI OLS4 API.
        
        Args:
            data: JSON response from the API
            
        Returns:
            List of UberonTerm objects
        """
        terms = []
        
        try:
            # EBI OLS4 API uses Solr-style response format
            if "response" in data and "docs" in data["response"]:
                results = data["response"]["docs"]
                logger.debug(f"Found {len(results)} results from EBI OLS4 API")
                
                for i, result in enumerate(results):
                    try:
                        logger.debug(f"Processing result {i+1}/{len(results)}: {result.get('id', '(no id)')} - {result.get('label', '(no label)')}")
                        
                        # Extract ID and ensure it's properly formatted
                        term_id = result.get("curie", result.get("id", ""))
                        logger.debug(f"Initial term_id from API: {term_id}")
                        
                        # Handle cases where obo_id might be different
                        if "obo_id" in result:
                            term_id = result["obo_id"]
                            logger.debug(f"Using obo_id instead: {term_id}")
                            
                        # Handle short_form which is used in EBI OLS4
                        if not term_id and "short_form" in result:
                            short_form = result["short_form"]
                            if short_form.startswith("UBERON_"):
                                term_id = short_form.replace("_", ":", 1)
                                logger.debug(f"Using short_form to create term_id: {term_id}")
                                
                        # Try to extract from IRI as last resort
                        if not term_id and "iri" in result:
                            iri = result["iri"]
                            if "UBERON_" in iri:
                                term_id = "UBERON:" + iri.split("UBERON_")[1]
                                logger.debug(f"Extracted term_id from IRI: {term_id}")
                        
                        if term_id and not term_id.startswith("UBERON:"):
                            # Handle differently formatted IDs
                            if term_id.startswith("UBERON_"):
                                term_id = term_id.replace("_", ":", 1)
                                logger.debug(f"Reformatted UBERON_ id to: {term_id}")
                            elif ":" not in term_id and term_id.isdigit():
                                term_id = f"UBERON:{term_id}"
                                logger.debug(f"Added UBERON prefix to numeric id: {term_id}")
                        
                        # Extract label
                        label = result.get("label", "")
                        
                        # Extract definition
                        definition = None
                        if "description" in result and result["description"]:
                            if isinstance(result["description"], list):
                                definition = result["description"][0]
                            else:
                                definition = result["description"]
                        # Try alternative field names
                        elif "definition" in result:
                            definition = result["definition"]
                            
                        # Extract synonyms
                        synonyms = []
                        if "synonym" in result and result["synonym"]:
                            if isinstance(result["synonym"], list):
                                synonyms = result["synonym"]
                            else:
                                synonyms = [result["synonym"]]
                        logger.debug(f"Found {len(synonyms)} synonyms")
                        
                        # Extract parent IDs
                        parent_ids = []
                        if "is_a" in result and result["is_a"]:
                            if isinstance(result["is_a"], list):
                                for parent in result["is_a"]:
                                    parent_id = parent
                                    if parent.startswith("UBERON_"):
                                        parent_id = parent.replace("_", ":", 1)
                                    parent_ids.append(parent_id)
                            else:
                                parent = result["is_a"]
                                parent_id = parent
                                if parent.startswith("UBERON_"):
                                    parent_id = parent.replace("_", ":", 1)
                                parent_ids.append(parent_id)
                        logger.debug(f"Found {len(parent_ids)} parent IDs")
                        
                        # Extract URL or construct one
                        url = result.get("iri", "")
                        if not url and term_id:
                            url = f"http://purl.obolibrary.org/obo/{term_id.replace(':', '_')}"
                        
                        # Only add terms with required fields
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
                            logger.debug(f"Added term: {term_id} - {label}")
                        else:
                            logger.warning(f"Skipping term with missing required fields. ID: {term_id}, Label: {label}")
                    
                    except Exception as e:
                        logger.error(f"Error parsing individual term from EBI OLS4 API response: {e}")
                        logger.debug(f"Problematic term data: {result}")
            else:
                logger.warning(f"Unexpected EBI OLS4 API response format. Available keys: {list(data.keys())}")
        
        except Exception as e:
            logger.error(f"Error parsing EBI OLS4 search results: {e}")
            logger.debug(f"API response data structure: {type(data)}")
            import traceback
            logger.debug(f"Exception traceback: {traceback.format_exc()}")
        
        logger.info(f"Successfully parsed {len(terms)} terms from search results")
        return terms
    
    def _parse_term_result(self, data: Dict[str, Any]) -> Optional[UberonTerm]:
        """
        Parse a single term result from the EBI OLS4 API.
        
        Args:
            data: JSON response from the API
            
        Returns:
            UberonTerm object or None if parsing fails
        """
        try:
            # Extract the term ID - in EBI OLS4 detailed term view, it's in the obo_id field
            # or can be extracted from the IRI
            term_id = data.get("obo_id", "")
            if not term_id:
                # Try to extract from IRI
                iri = data.get("iri", "")
                if iri and "UBERON_" in iri:
                    # Extract the ID portion from the IRI
                    term_id = "UBERON:" + iri.split("UBERON_")[1]
            
            # Extract label
            label = data.get("label", "")
            
            # Extract definition
            definition = None
            if "description" in data and data["description"]:
                if isinstance(data["description"], list):
                    definition = data["description"][0]
                else:
                    definition = data["description"]
            # Some EBI OLS4 responses use "definition" instead of "description"
            elif "definition" in data and data["definition"]:
                if isinstance(data["definition"], list):
                    definition = data["definition"][0]["definition"]
                else:
                    definition = data["definition"]
            
            # Extract synonyms - EBI OLS4 has a different structure for synonyms
            synonyms = []
            # Check in annotations which is where EBI OLS4 often puts synonyms
            if "annotation" in data:
                # Check for different synonym fields
                for syn_field in ["has_exact_synonym", "hasExactSynonym", "synonym"]:
                    if syn_field in data["annotation"]:
                        syns = data["annotation"][syn_field]
                        if isinstance(syns, list):
                            synonyms.extend(syns)
                        else:
                            synonyms.append(syns)
            # Also check direct synonym field
            elif "synonyms" in data and data["synonyms"]:
                for syn in data["synonyms"]:
                    if "synonym" in syn:
                        synonyms.append(syn["synonym"])
            
            # Extract parent IDs
            parent_ids = []
            # Check for parents/is_a in different fields
            if "parents" in data and data["parents"]:
                for parent in data["parents"]:
                    if "obo_id" in parent:
                        parent_ids.append(parent["obo_id"])
            elif "is_a" in data and data["is_a"]:
                if isinstance(data["is_a"], list):
                    for parent in data["is_a"]:
                        if isinstance(parent, str):
                            parent_ids.append(parent.replace("_", ":", 1) if parent.startswith("UBERON_") else parent)
                        elif isinstance(parent, dict) and "obo_id" in parent:
                            parent_ids.append(parent["obo_id"])
                else:
                    parent = data["is_a"]
                    if isinstance(parent, str):
                        parent_ids.append(parent.replace("_", ":", 1) if parent.startswith("UBERON_") else parent)
            
            # Use the IRI directly
            url = data.get("iri", "")
            if not url and term_id:
                url = f"http://purl.obolibrary.org/obo/{term_id.replace(':', '_')}"
            
            # Only create a term if we have the required fields
            if term_id and label:
                return UberonTerm(
                    id=term_id,
                    label=label,
                    definition=definition,
                    synonyms=synonyms,
                    parent_ids=parent_ids,
                    url=url
                )
            
            logger.warning(f"Could not extract required fields (ID and label) from term data")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing EBI OLS4 term result: {e}")
            logger.debug(f"Term data that could not be parsed: {data}")
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
            "colon": [
                UberonTerm(
                    id="UBERON:0001155",
                    label="colon",
                    definition="The region of the large intestine extending from the cecum to the rectum. It extracts moisture from food residues before they are eliminated.",
                    synonyms=["large bowel", "large intestine"],
                    parent_ids=["UBERON:0000160"],
                    url="http://purl.obolibrary.org/obo/UBERON_0001155"
                ),
                UberonTerm(
                    id="UBERON:0001153",
                    label="caecum",
                    definition="A pouch connected to the ascending colon, located at the intersection of the small and large intestines.",
                    synonyms=["cecum", "blind gut"],
                    parent_ids=["UBERON:0001155"],
                    url="http://purl.obolibrary.org/obo/UBERON_0001153"
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
    def check_api_health(cls, timeout: int = 10) -> Dict[str, Any]:
        """
        Class method to check the health of the EBI OLS4 API.
        
        This method can be used independently to diagnose API connectivity issues.
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary with API health information
        """
        from src.tools.check_api import check_ebi_ols4_api_health
        return check_ebi_ols4_api_health(timeout=timeout) 