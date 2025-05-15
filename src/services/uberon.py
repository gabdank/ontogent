"""
UBERON service for interacting with the UBERON ontology.

This module handles fetching data from UBERON ontology sources using the EBI OLS4 API
and converting the raw data into structured UberonTerm objects.
"""

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
        self.api_config = settings.UBERON_API
        
        # Construct API URLs
        self.search_url = f"{self.api_config.BASE_URL}{self.api_config.SEARCH_ENDPOINT}"
        self.term_url = f"{self.api_config.BASE_URL}{self.api_config.TERM_ENDPOINT}"
        
        logger.info(f"UBERON service initialized with API URL: {self.api_config.BASE_URL}")
        
        # Set up session with retry policy
        self.session = self._create_session()
        
        # Test API connection
        if not self.test_api_connection():
            logger.error("UBERON API is not accessible. Please check your network connection or API status.")
            raise ConnectionError("Cannot connect to UBERON API. Service is unavailable.")
    
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
            logger.info(f"Searching UBERON for: {query.query}")
            
            # Make the actual API call
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
                logger.error(f"Error sending request to EBI OLS4 API: {e}")
                raise ConnectionError(f"Failed to connect to UBERON API: {e}")
                
        except Exception as e:
            logger.error(f"Error searching UBERON terms: {e}")
            # Return an empty result in case of error
            return SearchResult(query=query.query)
    
    @log_with_context
    def get_term_by_id(self, term_id: str) -> Optional[UberonTerm]:
        """
        Get a single UBERON term by its ID.
        
        Args:
            term_id: The UBERON term ID (e.g., "UBERON:0000948")
            
        Returns:
            UberonTerm object if found, None otherwise
        """
        try:
            logger.info(f"Getting UBERON term by ID: {term_id}")
            
            # Format the term ID for the API
            formatted_id = term_id
            if ":" in term_id:
                # The EBI OLS4 API expects the ID to be URL-encoded and in a specific format
                ontology, code = term_id.split(":", 1)
                formatted_id = f"{ontology.lower()}:{code}"
            
            # Construct the URL for the specific term
            term_url = f"{self.term_url}/{urllib.parse.quote(formatted_id)}"
            
            logger.debug(f"Fetching term details from {term_url}")
            
            try:
                response = self.session.get(
                    term_url,
                    timeout=self.api_config.TIMEOUT
                )
                response.raise_for_status()
                
                # Parse the response
                data = response.json()
                logger.debug(f"Received term data with status code {response.status_code}")
                
                # Convert API response to a UberonTerm object
                term = self._parse_term_result(data)
                
                if term:
                    logger.info(f"Successfully retrieved term: {term.id} - {term.label}")
                else:
                    logger.warning(f"Term with ID {term_id} not found or could not be parsed")
                
                return term
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching term by ID from EBI OLS4 API: {e}")
                raise ConnectionError(f"Failed to connect to UBERON API: {e}")
                
        except Exception as e:
            logger.error(f"Error getting UBERON term by ID: {e}")
            return None
    
    def _parse_search_results(self, data: Dict[str, Any]) -> List[UberonTerm]:
        """
        Parse search results from the EBI OLS4 API response.
        
        Args:
            data: API response data
            
        Returns:
            List of UberonTerm objects
        """
        terms = []
        
        try:
            # Check if we have a valid response structure
            if "response" not in data or "docs" not in data["response"]:
                logger.warning("Invalid API response format for search results")
                return terms
            
            # Get the docs from the response
            docs = data["response"]["docs"]
            logger.debug(f"Found {len(docs)} docs in search results")
            
            # Process each document to create a UberonTerm
            for doc in docs:
                try:
                    # Extract the term ID
                    term_id = None
                    if "curie" in doc:
                        term_id = doc["curie"]
                    elif "obo_id" in doc:
                        term_id = doc["obo_id"]
                    elif "short_form" in doc:
                        # We need to reconstruct the ID from short_form and ontology
                        if "ontology_prefix" in doc:
                            term_id = f"{doc['ontology_prefix']}:{doc['short_form'].split('_')[-1]}"
                        else:
                            term_id = doc["short_form"].replace("_", ":", 1)
                    
                    if not term_id:
                        logger.warning(f"Could not extract term ID from doc: {doc}")
                        continue
                    
                    # Extract the label
                    label = doc.get("label") or doc.get("title") or doc.get("name")
                    if not label:
                        logger.warning(f"Could not extract label for term {term_id}")
                        continue
                    
                    # Extract the definition
                    definition = None
                    if "description" in doc and doc["description"]:
                        if isinstance(doc["description"], list):
                            definition = doc["description"][0]
                        else:
                            definition = doc["description"]
                    elif "def" in doc:
                        definition = doc["def"]
                    elif "obo_definition_citation" in doc:
                        if isinstance(doc["obo_definition_citation"], list) and len(doc["obo_definition_citation"]) > 0:
                            definition_entry = doc["obo_definition_citation"][0]
                            if isinstance(definition_entry, dict) and "definition" in definition_entry:
                                definition = definition_entry["definition"]
                    
                    # Extract synonyms
                    synonyms = []
                    if "synonym" in doc and doc["synonym"]:
                        synonyms = doc["synonym"] if isinstance(doc["synonym"], list) else [doc["synonym"]]
                    elif "obo_synonym" in doc and doc["obo_synonym"]:
                        for syn_entry in doc["obo_synonym"]:
                            if isinstance(syn_entry, dict) and "synonym" in syn_entry:
                                synonyms.append(syn_entry["synonym"])
                            elif isinstance(syn_entry, str):
                                synonyms.append(syn_entry)
                    
                    # Create the URL for the term
                    url = f"http://purl.obolibrary.org/obo/{term_id.replace(':', '_')}"
                    
                    # Create the UberonTerm object and add it to the list
                    term = UberonTerm(
                        id=term_id,
                        label=label,
                        definition=definition,
                        synonyms=synonyms,
                        parent_ids=[],  # We don't get parent IDs in the search results
                        url=url
                    )
                    
                    terms.append(term)
                    
                except Exception as e:
                    logger.warning(f"Error parsing individual term from search results: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(terms)} terms from search results")
            return terms
            
        except Exception as e:
            logger.error(f"Error parsing search results: {e}")
            return terms
    
    def _parse_term_result(self, data: Dict[str, Any]) -> Optional[UberonTerm]:
        """
        Parse a single term result from the EBI OLS4 API.
        
        Args:
            data: API response data for a single term
            
        Returns:
            UberonTerm object if successful, None otherwise
        """
        try:
            # Extract the term ID
            term_id = None
            if "curie" in data:
                term_id = data["curie"]
            elif "obo_id" in data:
                term_id = data["obo_id"]
            elif "short_form" in data:
                # We need to reconstruct the ID from short_form and ontology
                if "ontology_prefix" in data:
                    term_id = f"{data['ontology_prefix']}:{data['short_form'].split('_')[-1]}"
                else:
                    term_id = data["short_form"].replace("_", ":", 1)
            
            if not term_id:
                logger.warning("Could not extract term ID from response data")
                return None
            
            # Extract the label
            label = data.get("label") or data.get("title") or data.get("name")
            if not label:
                logger.warning(f"Could not extract label for term {term_id}")
                return None
            
            # Extract the definition
            definition = None
            if "description" in data and data["description"]:
                if isinstance(data["description"], list):
                    definition = data["description"][0]
                else:
                    definition = data["description"]
            elif "def" in data:
                definition = data["def"]
            elif "obo_definition_citation" in data:
                if isinstance(data["obo_definition_citation"], list) and len(data["obo_definition_citation"]) > 0:
                    definition_entry = data["obo_definition_citation"][0]
                    if isinstance(definition_entry, dict) and "definition" in definition_entry:
                        definition = definition_entry["definition"]
            
            # Extract synonyms
            synonyms = []
            if "synonym" in data and data["synonym"]:
                if isinstance(data["synonym"], list):
                    synonyms = data["synonym"]
                else:
                    synonyms = [data["synonym"]]
            elif "obo_synonym" in data and data["obo_synonym"]:
                for syn_entry in data["obo_synonym"]:
                    if isinstance(syn_entry, dict):
                        if "synonym" in syn_entry:
                            synonyms.append(syn_entry["synonym"])
                    elif isinstance(syn_entry, str):
                        for syns in syn_entry.split('",'):
                            syns = syns.strip('"')
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