"""
Unit tests for the LLMService class.

This module contains tests for verifying the functionality of the LLMService class,
including initialization, querying, and response parsing.
"""

import unittest
from unittest.mock import MagicMock, patch, ANY
import json

from src.services.llm import LLMService
from src.config import settings


class TestLLMService(unittest.TestCase):
    """Test cases for the LLMService class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Mock the anthropic client
        self.anthropic_client_mock = MagicMock()
        self.messages_mock = MagicMock()
        self.anthropic_client_mock.messages = self.messages_mock
        
        # Create a mock response object
        self.mock_response = MagicMock()
        self.mock_response.content = [MagicMock(text="Test response from LLM")]
        self.messages_mock.create.return_value = self.mock_response
        
        # Patch anthropic.Anthropic to return our mock
        self.anthropic_patch = patch('anthropic.Anthropic', return_value=self.anthropic_client_mock)
        self.anthropic_patch.start()
        
        # Create the service
        self.service = LLMService()
    
    def tearDown(self):
        """Clean up after each test method."""
        self.anthropic_patch.stop()
    
    def test_init_success(self):
        """Test successful initialization of the LLM service."""
        # Check that client was initialized with the correct API key
        self.assertEqual(self.service.client, self.anthropic_client_mock)
        self.assertEqual(self.service.model, settings.MODEL_NAME)
        self.assertEqual(self.service.max_tokens, settings.MAX_TOKENS)
        self.assertEqual(self.service.temperature, settings.TEMPERATURE)
    
    def test_init_failure(self):
        """Test error handling during initialization."""
        # Stop the current patch so we can create a new one
        self.anthropic_patch.stop()
        
        # Create a new patch that raises an exception
        with patch('anthropic.Anthropic', side_effect=Exception("API key error")):
            with self.assertRaises(Exception):
                LLMService()
    
    def test_query_success(self):
        """Test successful query to the LLM."""
        prompt = "What is the heart?"
        system_prompt = "You are a helpful assistant."
        
        result = self.service.query(prompt, system_prompt)
        
        # Check that the client was called with the correct arguments
        self.messages_mock.create.assert_called_once_with(
            model=settings.MODEL_NAME,
            max_tokens=settings.MAX_TOKENS,
            temperature=settings.TEMPERATURE,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Check that the result is as expected
        self.assertEqual(result, "Test response from LLM")
    
    def test_query_error(self):
        """Test error handling during query."""
        # Make the create method raise an exception
        self.messages_mock.create.side_effect = Exception("API error")
        
        # Call the method and check for the exception
        with self.assertRaises(Exception):
            self.service.query("Test prompt")
    
    def test_analyze_uberon_query_success(self):
        """Test successful analysis of a UBERON query."""
        # Set up a valid JSON response
        json_response = {
            "extracted_concepts": ["heart"],
            "possible_uberon_terms": ["heart", "cardiac muscle"],
            "recommended_search_query": "heart",
            "explanation": "The query is about the heart."
        }
        
        # Update the mock to return the JSON as a string
        self.mock_response.content[0].text = json.dumps(json_response)
        
        # Call the method
        user_query = "What is the heart?"
        result = self.service.analyze_uberon_query(user_query)
        
        # Verify the result
        self.assertIn("raw_response", result)
        # Parse the raw response to verify it matches the expected JSON
        parsed_response = json.loads(result["raw_response"])
        self.assertEqual(parsed_response, json_response)
        
        # Verify the query method was called correctly
        self.messages_mock.create.assert_called_once()
    
    def test_analyze_uberon_query_with_context(self):
        """Test analysis with additional context."""
        # Set up the response
        self.mock_response.content[0].text = json.dumps({"test": "response"})
        
        # Call the method with context
        user_query = "What is the heart?"
        context = "The heart is a muscular organ."
        result = self.service.analyze_uberon_query(user_query, context)
        
        # Verify the query method was called with the context included
        create_call = self.messages_mock.create.call_args
        messages_param = create_call.kwargs["messages"][0]["content"]
        self.assertIn(user_query, messages_param)
        self.assertIn(context, messages_param)
    
    def test_analyze_uberon_query_invalid_json(self):
        """Test handling of invalid JSON responses."""
        # Set up an invalid JSON response
        self.mock_response.content[0].text = "Not valid JSON"
        
        # Call the method
        result = self.service.analyze_uberon_query("What is the heart?")
        
        # Verify the result still contains the raw response
        self.assertIn("raw_response", result)
        self.assertEqual(result["raw_response"], "Not valid JSON")
    
    def test_analyze_uberon_query_error(self):
        """Test error handling during analysis."""
        # Make the query method raise an exception
        self.messages_mock.create.side_effect = Exception("API error")
        
        # Call the method and check for the exception
        with self.assertRaises(Exception):
            self.service.analyze_uberon_query("Test query")


if __name__ == "__main__":
    unittest.main() 