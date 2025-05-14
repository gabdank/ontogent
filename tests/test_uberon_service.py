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
        # Save original settings to restore after tests
        self.original_dev_mode = settings.DEV_MODE
        
        # Create mock session and response
        self.mock_session = MagicMock()
        self.mock_response = MagicMock()
        self.mock_response.status_code = 200
        self.mock_session.get.return_value = self.mock_response
        
        # Sample search responses
        self.sample_api_search_response = {
            "results": [
                {
                    "id": "UBERON:0000948",
                    "label": "heart",
                    "definition": "A hollow, muscular organ...",
                    "synonyms": ["cardiac muscle"],
                    "parents": ["UBERON:0000077"],
                    "url": "http://purl.obolibrary.org/obo/UBERON_0000948"
                },
                {
                    "id": "UBERON:0004146",
                    "label": "primitive heart",
                    "definition": "The developing heart...",
                    "synonyms": ["embryonic heart"],
                    "parents": ["UBERON:0000948"],
                    "url": "http://purl.obolibrary.org/obo/UBERON_0004146"
                }
            ]
        }
        
        # Sample term response
        self.sample_api_term_response = {
            "term": {
                "id": "UBERON:0000948",
                "label": "heart",
                "definition": "A hollow, muscular organ...",
                "synonyms": ["cardiac muscle"],
                "parents": ["UBERON:0000077"],
                "url": "http://purl.obolibrary.org/obo/UBERON_0000948"
            }
        }
    
    def tearDown(self):
        """Clean up after each test method."""
        # Restore original settings
        settings.DEV_MODE = self.original_dev_mode
    
    @patch('src.services.uberon.settings.DEV_MODE', True)
    def test_search_dev_mode(self):
        """Test search in development mode with mock data."""
        # Initialize the service
        service = UberonService()
        
        # Create a search query
        query = SearchQuery(query="heart")
        
        # Call the search method
        result = service.search(query)
        
        # Verify the results
        self.assertEqual(result.query, "heart")
        self.assertEqual(result.total_matches, 2)
        self.assertEqual(result.best_match.id, "UBERON:0000948")
        self.assertEqual(result.best_match.label, "heart")
    
    @patch('src.services.uberon.settings.DEV_MODE', False)
    @patch('src.services.uberon.requests.Session')
    def test_search_production_mode(self, mock_session_class):
        """Test search in production mode with API calls."""
        # Set up mock response
        mock_session = MagicMock()
        mock_response = MagicMock()
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
        self.assertTrue(call_args[0][0].endswith("/search"))
        self.assertEqual(call_args[1]["params"]["q"], "heart")
        self.assertEqual(call_args[1]["params"]["max_results"], 5)
        
        # Verify the results were parsed correctly
        self.assertEqual(result.query, "heart")
        self.assertEqual(result.total_matches, 2)
        self.assertEqual(result.best_match.id, "UBERON:0000948")
        self.assertEqual(result.best_match.label, "heart")
    
    @patch('src.services.uberon.settings.DEV_MODE', True)
    def test_get_term_by_id_dev_mode(self):
        """Test get_term_by_id in development mode with mock data."""
        # Initialize the service
        service = UberonService()
        
        # Known term ID
        term_id = "UBERON:0000948"
        
        # Call the method
        term = service.get_term_by_id(term_id)
        
        # Verify the result
        self.assertIsNotNone(term)
        self.assertEqual(term.id, term_id)
        self.assertEqual(term.label, "heart")
        
        # Try with unknown term ID
        unknown_term = service.get_term_by_id("UBERON:9999999")
        self.assertIsNone(unknown_term)
    
    @patch('src.services.uberon.settings.DEV_MODE', False)
    @patch('src.services.uberon.requests.Session')
    def test_get_term_by_id_production_mode(self, mock_session_class):
        """Test get_term_by_id in production mode with API calls."""
        # Set up mock response
        mock_session = MagicMock()
        mock_response = MagicMock()
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
        mock_session.get.assert_called_once()
        
        # Verify the API call parameters
        call_args = mock_session.get.call_args
        self.assertTrue(call_args[0][0].endswith("/term"))
        self.assertEqual(call_args[1]["params"]["id"], term_id)
        
        # Verify the result was parsed correctly
        self.assertIsNotNone(term)
        self.assertEqual(term.id, term_id)
        self.assertEqual(term.label, "heart")
    
    @patch('src.services.uberon.settings.DEV_MODE', False)
    @patch('src.services.uberon.requests.Session')
    def test_api_error_handling(self, mock_session_class):
        """Test error handling for API failures."""
        # Set up mock response for an error
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.exceptions.RequestException("API error")
        mock_session_class.return_value = mock_session
        
        # Initialize the service
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


if __name__ == "__main__":
    unittest.main() 