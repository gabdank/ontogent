"""
Unit tests for the UberonService class.

This module contains tests for verifying the functionality of the UberonService class,
including API interactions and response parsing.
"""

import unittest
from unittest.mock import MagicMock, patch, ANY
import json
import requests
import urllib.parse

from src.services.uberon import UberonService
from src.models.uberon import UberonTerm, SearchQuery
from src.config import settings


class TestUberonService(unittest.TestCase):
    """Test cases for the UberonService class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create mock session and response
        self.mock_session = MagicMock()
        self.mock_response = MagicMock()
        self.mock_response.status_code = 200
        self.mock_session.get.return_value = self.mock_response
        
        # Mock the API connection test to return True
        self.connection_patcher = patch.object(UberonService, 'test_api_connection')
        self.mock_test_connection = self.connection_patcher.start()
        self.mock_test_connection.return_value = True
        
        # Sample search response in EBI OLS4 format
        self.sample_api_search_response = {
            "response": {
                "numFound": 2,
                "start": 0,
                "docs": [
                    {
                        "id": "http://purl.obolibrary.org/obo/UBERON_0000948",
                        "short_form": "UBERON_0000948",
                        "obo_id": "UBERON:0000948",
                        "label": "heart",
                        "description": ["A hollow, muscular organ..."],
                        "synonym": ["cardiac muscle"],
                        "ontology_name": "uberon"
                    },
                    {
                        "id": "http://purl.obolibrary.org/obo/UBERON_0004146",
                        "short_form": "UBERON_0004146",
                        "obo_id": "UBERON:0004146",
                        "label": "primitive heart",
                        "description": ["The developing heart..."],
                        "synonym": ["embryonic heart"],
                        "ontology_name": "uberon"
                    }
                ]
            }
        }
        
        # Sample term response in EBI OLS4 format
        self.sample_api_term_response = {
            "id": "http://purl.obolibrary.org/obo/UBERON_0000948",
            "label": "heart",
            "description": ["A hollow, muscular organ..."],
            "annotation": {
                "has_exact_synonym": ["cardiac muscle"]
            },
            "obo_id": "UBERON:0000948",
            "short_form": "UBERON_0000948",
            "ontology_name": "uberon",
            "is_a": ["http://purl.obolibrary.org/obo/UBERON_0000077"]
        }
    
    def tearDown(self):
        """Clean up after each test method."""
        self.connection_patcher.stop()
    
    @patch('src.services.uberon.requests.Session')
    def test_search(self, mock_session_class):
        """Test search with mocked API responses."""
        # Set up mock response
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_api_search_response
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        # Initialize the service
        service = UberonService()
        
        # Create a search query
        query = SearchQuery(query="heart", max_results=5)
        
        # Call the search method
        result = service.search(query)
        
        # Verify the session was created and used correctly
        mock_session_class.assert_called_once()
        mock_session.get.assert_called_once()
        
        # Verify the API call parameters
        call_args = mock_session.get.call_args
        self.assertTrue('/search' in call_args[0][0])
        self.assertEqual(call_args[1]["params"]["q"], "heart")
        self.assertEqual(call_args[1]["params"]["rows"], 5)
        
        # Verify the results were parsed correctly
        self.assertEqual(result.query, "heart")
        self.assertGreater(result.total_matches, 0)
        self.assertEqual(result.matches[0].id, "UBERON:0000948")
        self.assertEqual(result.matches[0].label, "heart")
    
    @patch('src.services.uberon.requests.Session')
    def test_get_term_by_id(self, mock_session_class):
        """Test get_term_by_id with mocked API responses."""
        # Set up mock response
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_api_term_response
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        # Initialize the service
        service = UberonService()
        
        # Term ID to look up
        term_id = "UBERON:0000948"
        
        # Call the method
        term = service.get_term_by_id(term_id)
        
        # Verify the session was created and used correctly
        mock_session_class.assert_called_once()
        self.assertTrue(mock_session.get.called)
        
        # Verify the result was parsed correctly
        self.assertIsNotNone(term)
        self.assertEqual(term.id, term_id)
        self.assertEqual(term.label, "heart")
    
    @patch('src.services.uberon.requests.Session')
    def test_api_error_handling(self, mock_session_class):
        """Test error handling for API failures."""
        # Set up mock response for an error
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.exceptions.RequestException("API error")
        mock_session_class.return_value = mock_session
        
        # Initialize the service with mocked test_api_connection to avoid ConnectionError during initialization
        service = UberonService()
        
        # Create a search query
        query = SearchQuery(query="heart")
        
        # Call the search method - should handle the error
        result = service.search(query)
        
        # Verify the results show an empty search result
        self.assertEqual(result.query, "heart")
        self.assertEqual(result.total_matches, 0)
        self.assertIsNone(result.best_match)
        
        # Also test get_term_by_id error handling
        term = service.get_term_by_id("UBERON:0000948")
        self.assertIsNone(term)
    
    @patch('src.services.uberon.requests.Session')
    def test_connection_failure(self, mock_session_class):
        """Test handling of connection failures during initialization."""
        # Set up mock session to simulate connection failure
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.exceptions.RequestException("Connection error")
        mock_session_class.return_value = mock_session
        
        # Override the mocked test_api_connection to let the real one run
        self.connection_patcher.stop()
        
        # Attempting to initialize the service should raise ConnectionError
        with self.assertRaises(ConnectionError):
            service = UberonService()

    # Tests for test_api_connection method itself
    @patch('src.services.uberon.requests.Session')
    def test_test_api_connection_success(self, mock_session_class):
        """Test test_api_connection when API is healthy."""
        mock_session_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Simulate a valid API response structure
        mock_response.json.return_value = {"response": {"docs": [{"id": "test"}]}}
        mock_session_instance.get.return_value = mock_response
        mock_session_class.return_value = mock_session_instance

        self.connection_patcher.stop() # Stop the default patch
        service = UberonService() # This will now call the real test_api_connection with mocks
        self.connection_patcher.start() # Restart patch for other tests

        self.assertTrue(service.test_api_connection()) # Call it again to assert its direct return

    @patch('src.services.uberon.requests.Session')
    def test_test_api_connection_unexpected_data_format(self, mock_session_class):
        """Test test_api_connection with 200 OK but unexpected data format."""
        mock_session_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"unexpected_key": "data"} # Invalid structure
        mock_session_instance.get.return_value = mock_response
        mock_session_class.return_value = mock_session_instance

        self.connection_patcher.stop() # Stop the default patch from setUp
        # Instantiation will call test_api_connection, which should return False here,
        # leading to ConnectionError from __init__.
        with self.assertRaisesRegex(ConnectionError, "Cannot connect to UBERON API. Service is unavailable."):
            UberonService()
        self.connection_patcher.start() # Restart patch for other tests

    @patch('src.services.uberon.requests.Session')
    def test_test_api_connection_http_error(self, mock_session_class):
        """Test test_api_connection with a non-200 HTTP status code."""
        mock_session_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 503 # Service Unavailable
        mock_session_instance.get.return_value = mock_response
        mock_session_class.return_value = mock_session_instance

        self.connection_patcher.stop()
        with self.assertRaisesRegex(ConnectionError, "Cannot connect to UBERON API. Service is unavailable."):
            UberonService()
        self.connection_patcher.start()

    @patch('src.services.uberon.requests.Session')
    def test_test_api_connection_request_exception(self, mock_session_class):
        """Test test_api_connection when a RequestException occurs."""
        mock_session_instance = MagicMock()
        mock_session_instance.get.side_effect = requests.exceptions.RequestException("Network Error")
        mock_session_class.return_value = mock_session_instance

        self.connection_patcher.stop()
        with self.assertRaisesRegex(ConnectionError, "Cannot connect to UBERON API. Service is unavailable."):
            UberonService()
        self.connection_patcher.start()

    @patch('src.services.uberon.requests.Session')
    def test_test_api_connection_unexpected_exception(self, mock_session_class):
        """Test test_api_connection when an unexpected Exception occurs."""
        mock_session_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = Exception("Unexpected parsing error")
        mock_session_instance.get.return_value = mock_response
        mock_session_class.return_value = mock_session_instance

        self.connection_patcher.stop()
        with self.assertRaisesRegex(ConnectionError, "Cannot connect to UBERON API. Service is unavailable."):
            UberonService()
        self.connection_patcher.start()

    # Additional tests for search method
    @patch('src.services.uberon.requests.Session')
    def test_search_main_exception_block(self, mock_session_class):
        """Test the main exception block in the search method."""
        # To trigger the main exception block, we can make _parse_search_results fail
        mock_session_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_api_search_response # Valid API response
        mock_session_instance.get.return_value = mock_response
        mock_session_class.return_value = mock_session_instance

        service = UberonService()
        
        with patch.object(service, '_parse_search_results', side_effect=Exception("Parsing Boom!")):
            query = SearchQuery(query="heart")
            result = service.search(query)
            self.assertEqual(result.query, query.query)
            self.assertEqual(result.total_matches, 0)
            self.assertIn("Error: Parsing Boom!", result.reasoning)

    @patch('src.services.uberon.requests.Session')
    def test_search_empty_docs_or_no_numFound(self, mock_session_class):
        """Test search when API returns 200 but with empty docs or no numFound."""
        mock_session_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Simulate API response with no docs
        mock_response.json.return_value = {"response": {"numFound": 0, "docs": []}}
        mock_session_instance.get.return_value = mock_response
        mock_session_class.return_value = mock_session_instance

        service = UberonService()
        query = SearchQuery(query="rare_term")
        result = service.search(query)

        self.assertEqual(result.total_matches, 0)
        self.assertEqual(result.reasoning, "No UBERON terms matched the query")

        # Simulate API response with docs but numFound is missing (should still work if docs are parsed)
        mock_response.json.return_value = {"response": {"docs": [self.sample_api_search_response["response"]["docs"][0]]}}
        result_numfound_missing = service.search(query)
        # Based on current code, if docs exist, it proceeds. numFound is for logging.
        self.assertEqual(result_numfound_missing.total_matches, 1)

    @patch('src.services.uberon.requests.Session')
    def test_search_request_exception_then_connection_error(self, mock_session_class):
        """Test search raises ConnectionError on requests.exceptions.RequestException."""
        mock_session_instance = MagicMock()
        mock_session_instance.get.side_effect = requests.exceptions.Timeout("API Timed Out")
        mock_session_class.return_value = mock_session_instance

        service = UberonService()
        query = SearchQuery(query="heart")
        
        # The code catches RequestException and then returns an empty SearchResult with error in reasoning
        # It does not re-raise ConnectionError directly in search, but logs it.
        # The ConnectionError is raised from __init__ or get_term_by_id if session calls fail.
        # Let's verify the SearchResult reflects the error as per current search() implementation.
        result = service.search(query)
        self.assertEqual(result.query, "heart")
        self.assertEqual(result.total_matches, 0)
        # The actual error message in reasoning includes the specific exception string.
        expected_reasoning = f"Error: Failed to connect to UBERON API: API Timed Out"
        self.assertEqual(result.reasoning, expected_reasoning)

    # Additional tests for get_term_by_id method
    @patch('src.services.uberon.requests.Session')
    def test_get_term_by_id_no_colon_in_id(self, mock_session_class):
        """Test get_term_by_id URL construction when term_id has no colon."""
        mock_session_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        # For this test, the content of json() doesn't matter as much as _parse_term_result behavior
        mock_response.json.return_value = {} # Minimal valid JSON
        mock_session_instance.get.return_value = mock_response
        mock_session_class.return_value = mock_session_instance

        service = UberonService()
        term_id_no_colon = "UBERON_0000948"

        # Mock _parse_term_result to return a dummy term to prevent None return from get_term_by_id
        # This allows us to focus on the URL call.
        dummy_term = UberonTerm(id=term_id_no_colon, label="test", definition="test def")
        with patch.object(service, '_parse_term_result', return_value=dummy_term):
            term = service.get_term_by_id(term_id_no_colon)
        
        self.assertIsNotNone(term)
        self.assertEqual(term.id, term_id_no_colon)

        # Test the actual URL called: if term_id has no colon, formatted_id = term_id. Then it's URL quoted.
        # The API endpoint is self.term_url which ends with /terms
        # So, expected_full_url_part = "http://example.com/api/terms/UBERON_0000948"
        # We need to check the argument to session.get()
        
        # service.term_url is f"{self.api_config.BASE_URL}{self.api_config.TERM_ENDPOINT}"
        # settings.UBERON_API.BASE_URL + settings.UBERON_API.TERM_ENDPOINT + / + term_id_no_colon (URL encoded)
        # Example: http://localhost:8080/api/ontologies/uberon/terms/UBERON_0000948
        
        # The actual call is to: f"{service.term_url}/{urllib.parse.quote(formatted_id)}"
        # where formatted_id is term_id_no_colon if no colon is present.
        expected_called_url = f"{service.term_url}/{urllib.parse.quote(term_id_no_colon)}"
        mock_session_instance.get.assert_called_once_with(
            expected_called_url,
            timeout=service.api_config.TIMEOUT
        )

    @patch('src.services.uberon.requests.Session')
    def test_get_term_by_id_parse_returns_none(self, mock_session_class):
        """Test get_term_by_id when _parse_term_result returns None."""
        mock_session_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"invalid_data": True} # Data that _parse_term_result can't handle
        mock_session_instance.get.return_value = mock_response
        mock_session_class.return_value = mock_session_instance

        service = UberonService()
        with patch.object(service, '_parse_term_result', return_value=None):
            term = service.get_term_by_id("UBERON:0000123")
            self.assertIsNone(term)

    @patch('src.services.uberon.requests.Session')
    def test_get_term_by_id_main_exception_block(self, mock_session_class):
        """Test the main exception block in get_term_by_id."""
        mock_session_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_api_term_response
        mock_session_instance.get.return_value = mock_response
        mock_session_class.return_value = mock_session_instance

        service = UberonService()
        # To hit the main exception, make _parse_term_result raise an unexpected error
        with patch.object(service, '_parse_term_result', side_effect=Exception("Parsing Oops!")):
            term = service.get_term_by_id("UBERON:0000948")
            self.assertIsNone(term) # Should return None as per current code

    @patch('src.services.uberon.requests.Session')
    def test_get_term_by_id_request_exception_then_connection_error(self, mock_session_class):
        """Test get_term_by_id raises ConnectionError on requests.exceptions.RequestException."""
        mock_session_instance = MagicMock()
        mock_session_instance.get.side_effect = requests.exceptions.HTTPError("API Server Error")
        mock_session_class.return_value = mock_session_instance

        service = UberonService()
        # The outer try-except in get_term_by_id catches all exceptions and returns None.
        # It also logs the error. The inner try-except for API call raises ConnectionError.
        # This ConnectionError is then caught by the outer block.
        term = service.get_term_by_id("UBERON:0000948")
        self.assertIsNone(term)
        # We can also check logs if needed, e.g. with self.assertLogs
        # For now, ensuring None is returned is the primary check based on current code structure.

    @patch('src.services.uberon.requests.Session')
    def test_search_malformed_term_data(self, mock_session_class):
        """Test handling of malformed term data in search results."""
        # Set up mock response with malformed term data
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Create a response with missing required fields
        malformed_response = {
            "response": {
                "numFound": 2,
                "start": 0,
                "docs": [
                    {
                        "id": "http://purl.obolibrary.org/obo/UBERON_0000948",
                        # Missing label field
                        "description": ["A hollow, muscular organ..."],
                        "ontology_name": "uberon"
                    },
                    {
                        "id": "http://purl.obolibrary.org/obo/UBERON_0004146",
                        "label": "primitive heart",
                        # Missing description field
                        "ontology_name": "uberon"
                    }
                ]
            }
        }
        mock_response.json.return_value = malformed_response
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        # Initialize the service
        service = UberonService()
        
        # Create a search query
        query = SearchQuery(query="heart", max_results=5)
        
        # Call the search method
        result = service.search(query)
        
        # Verify the results were handled gracefully
        self.assertEqual(result.query, "heart")
        self.assertEqual(result.total_matches, 0)  # Should have no valid matches
        self.assertEqual(len(result.matches), 0)  # Should have filtered out malformed terms
        self.assertIsNone(result.best_match)
        self.assertEqual(result.reasoning, "No UBERON terms matched the query")  # Actual message from the code


if __name__ == "__main__":
    unittest.main() 