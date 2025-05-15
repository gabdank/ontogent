"""
Unit tests for the UberonService class.

This module contains tests for verifying the functionality of the UberonService class,
including API interactions and response parsing.
"""

import unittest
from unittest.mock import MagicMock, patch, ANY
import json
import requests

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


if __name__ == "__main__":
    unittest.main() 