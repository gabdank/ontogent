"""
Unit tests for error handling in the UberonAgent class.

This module contains tests specifically focused on error paths and exception handling
in the UberonAgent class to improve code coverage for these less-tested areas.
"""

import unittest
from unittest.mock import MagicMock, patch
import json

from src.services.agent import UberonAgent
from src.models.uberon import UberonTerm, SearchResult, SearchQuery


class TestUberonAgentErrorHandling(unittest.TestCase):
    """Test cases for error handling in the UberonAgent class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create mock LLM and UBERON services
        self.mock_llm_service = MagicMock()
        self.mock_uberon_service = MagicMock()
        
        # Create sample test data
        self.sample_heart_term = UberonTerm(
            id="UBERON:0000948",
            label="heart",
            definition="A hollow, muscular organ...",
            synonyms=["cardiac muscle"],
            parent_ids=["UBERON:0000077"],
            url="http://purl.obolibrary.org/obo/UBERON_0000948"
        )
        
        # Create the agent with mocked services
        with patch('src.services.agent.LLMService', return_value=self.mock_llm_service), \
             patch('src.services.agent.UberonService', return_value=self.mock_uberon_service):
            self.agent = UberonAgent()
    
    def test_init_error(self):
        """Test initialization error handling."""
        # Make LLMService initialization fail
        with patch('src.services.agent.LLMService', side_effect=Exception("API key error")):
            with self.assertRaises(Exception):
                UberonAgent()
    
    def test_find_term_llm_error(self):
        """Test error handling when LLM service fails."""
        # Set up the LLM service to raise an exception
        self.mock_llm_service.analyze_uberon_query.side_effect = Exception("LLM API error")
        
        # Call the method and check that it returns an empty result
        result = self.agent.find_term("heart")
        
        # Verify the result is a SearchResult with the query but no matches
        self.assertIsInstance(result, SearchResult)
        self.assertEqual(result.query, "heart")
        self.assertEqual(result.total_matches, 0)
        self.assertIsNone(result.best_match)
    
    def test_find_term_uberon_error(self):
        """Test error handling when UBERON service fails."""
        # Set up the LLM service to return a normal response
        self.mock_llm_service.analyze_uberon_query.return_value = {
            "raw_response": json.dumps({
                "recommended_search_query": "heart"
            })
        }
        
        # Set up the UBERON service to raise an exception
        self.mock_uberon_service.search.side_effect = Exception("UBERON API error")
        
        # Call the method and check that it returns an empty result
        result = self.agent.find_term("heart")
        
        # Verify the result is a SearchResult with the query but no matches
        self.assertIsInstance(result, SearchResult)
        self.assertEqual(result.query, "heart")
        self.assertEqual(result.total_matches, 0)
        self.assertIsNone(result.best_match)
    
    def test_find_term_invalid_json_from_llm(self):
        """Test handling of invalid JSON from LLM service."""
        # Set up the LLM service to return an invalid JSON response
        self.mock_llm_service.analyze_uberon_query.return_value = {
            "raw_response": "Not valid JSON"
        }
        
        # Call the method
        result = self.agent.find_term("heart")
        
        # Verify that the method still proceeded and called the UBERON service
        self.mock_uberon_service.search.assert_called_once()
        
        # Verify that it used the original query as fallback
        call_args = self.mock_uberon_service.search.call_args[0][0]
        self.assertEqual(call_args.query, "heart")
    
    def test_find_term_partially_valid_json_from_llm(self):
        """Test handling of partially valid JSON from LLM service."""
        # Set up the LLM service to return a partial JSON response
        self.mock_llm_service.analyze_uberon_query.return_value = {
            "raw_response": '{"start": "good" but then invalid'
        }
        
        # Call the method
        result = self.agent.find_term("heart")
        
        # Verify that the method still proceeded and called the UBERON service
        self.mock_uberon_service.search.assert_called_once()
        
        # Verify that it used the original query as fallback
        call_args = self.mock_uberon_service.search.call_args[0][0]
        self.assertEqual(call_args.query, "heart")
    
    def test_rank_terms_llm_error(self):
        """Test error handling in the term ranking function."""
        # Create terms to rank
        terms = [self.sample_heart_term]
        
        # Set up the LLM service to raise an exception
        self.mock_llm_service.query.side_effect = Exception("LLM API error")
        
        # Call the ranking method directly
        result = self.agent._rank_terms("heart", terms)
        
        # Verify the result is None
        self.assertIsNone(result)
    
    def test_rank_terms_invalid_json(self):
        """Test handling of invalid JSON in term ranking."""
        # Create terms to rank
        terms = [self.sample_heart_term]
        
        # Set up the LLM service to return non-JSON
        self.mock_llm_service.query.return_value = "Not valid JSON"
        
        # Call the ranking method directly
        result = self.agent._rank_terms("heart", terms)
        
        # Verify the result uses the first term as fallback
        self.assertEqual(result["term"], self.sample_heart_term)
        self.assertEqual(result["confidence"], 0.7)
        self.assertIn("most relevant", result["reasoning"])
    
    def test_rank_terms_with_non_matching_id(self):
        """Test ranking when the LLM returns an ID that doesn't match any term."""
        # Create terms to rank
        terms = [self.sample_heart_term]
        
        # Set up the LLM service to return a non-matching ID
        self.mock_llm_service.query.return_value = json.dumps({
            "best_match_id": "UBERON:9999999",
            "confidence": 0.8,
            "reasoning": "This is the best match"
        })
        
        # Call the ranking method directly
        result = self.agent._rank_terms("heart", terms)
        
        # Verify the result uses the first term as fallback
        self.assertEqual(result["term"], self.sample_heart_term)
    
    def test_rank_terms_without_best_match_id(self):
        """Test ranking when the LLM returns JSON without a best_match_id."""
        # Create terms to rank
        terms = [self.sample_heart_term]
        
        # Set up the LLM service to return JSON without best_match_id
        self.mock_llm_service.query.return_value = json.dumps({
            "confidence": 0.8,
            "reasoning": "This is the best match"
        })
        
        # Call the ranking method directly
        result = self.agent._rank_terms("heart", terms)
        
        # Verify the result uses the first term as fallback
        self.assertEqual(result["term"], self.sample_heart_term)


if __name__ == "__main__":
    unittest.main() 