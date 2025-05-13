"""
Unit tests for the UberonAgent class.

This module contains tests for verifying the functionality of the UberonAgent class,
including query analysis, term searching, and result ranking.
"""

import unittest
from unittest.mock import MagicMock, patch
import json

from src.services.agent import UberonAgent
from src.models.uberon import UberonTerm, SearchResult, SearchQuery


class TestUberonAgent(unittest.TestCase):
    """Test cases for the UberonAgent class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create mock LLM and UBERON services
        self.mock_llm_service = MagicMock()
        self.mock_uberon_service = MagicMock()
        
        # Create sample test data
        self.sample_heart_term = UberonTerm(
            id="UBERON:0000948",
            label="heart",
            definition="A hollow, muscular organ, which, by contracting rhythmically, keeps up the circulation of the blood.",
            synonyms=["cardiac muscle"],
            parent_ids=["UBERON:0000077"],
            url="http://purl.obolibrary.org/obo/UBERON_0000948"
        )
        
        self.sample_primitive_heart_term = UberonTerm(
            id="UBERON:0004146",
            label="primitive heart",
            definition="The developing heart at the cardiac crescent stage.",
            synonyms=["embryonic heart"],
            parent_ids=["UBERON:0000948"],
            url="http://purl.obolibrary.org/obo/UBERON_0004146"
        )
        
        # Mock LLM response for query analysis
        self.mock_llm_service.analyze_uberon_query.return_value = {
            "raw_response": json.dumps({
                "extracted_concepts": ["heart"],
                "possible_uberon_terms": ["heart", "primitive heart"],
                "recommended_search_query": "heart",
                "explanation": "The query mentions the heart, which is a well-defined anatomical structure."
            })
        }
        
        # Mock UBERON search response
        self.mock_uberon_service.search.return_value = SearchResult(
            query="heart",
            matches=[self.sample_heart_term, self.sample_primitive_heart_term],
            total_matches=2,
            best_match=self.sample_heart_term,
            confidence=0.9,
            reasoning="This term directly matches the user's query."
        )
        
        # Create the agent with mocked services
        with patch('src.services.agent.LLMService', return_value=self.mock_llm_service), \
             patch('src.services.agent.UberonService', return_value=self.mock_uberon_service):
            self.agent = UberonAgent()
    
    def test_find_term_with_exact_match(self):
        """Test finding a term with an exact match in the ontology."""
        # Define test input
        query = "heart"
        
        # Call the method under test
        result = self.agent.find_term(query)
        
        # Verify the results
        self.assertEqual(result.query, query)
        self.assertEqual(result.total_matches, 2)
        self.assertEqual(result.best_match.id, "UBERON:0000948")
        self.assertEqual(result.best_match.label, "heart")
        self.assertGreaterEqual(result.confidence, 0.8)
        
        # Verify the LLM service was called correctly
        self.mock_llm_service.analyze_uberon_query.assert_called_once_with(query)
        
        # Verify the UBERON service was called correctly
        self.mock_uberon_service.search.assert_called_once()
        actual_search_query = self.mock_uberon_service.search.call_args[0][0]
        self.assertEqual(actual_search_query.query, query)
    
    def test_find_term_with_no_matches(self):
        """Test finding a term with no matches in the ontology."""
        # Define test input
        query = "nonexistent organ"
        
        # Mock UBERON search to return no matches
        self.mock_uberon_service.search.return_value = SearchResult(
            query=query,
            matches=[],
            total_matches=0,
            best_match=None,
            confidence=None,
            reasoning=None
        )
        
        # Call the method under test
        result = self.agent.find_term(query)
        
        # Verify the results
        self.assertEqual(result.query, query)
        self.assertEqual(result.total_matches, 0)
        self.assertIsNone(result.best_match)
        self.assertIsNone(result.confidence)
        
        # Verify the LLM service was called correctly
        self.mock_llm_service.analyze_uberon_query.assert_called_once_with(query)
        
        # Verify the UBERON service was called correctly
        self.mock_uberon_service.search.assert_called_once()
    
    def test_find_term_with_multiple_matches(self):
        """Test finding a term with multiple matches that need to be ranked."""
        # Define test input
        query = "embryonic heart"
        
        # Set up the mock to return multiple matches with no clear best match
        search_result = SearchResult(
            query=query,
            matches=[self.sample_heart_term, self.sample_primitive_heart_term],
            total_matches=2,
            best_match=None,  # No best match yet
            confidence=None,
            reasoning=None
        )
        self.mock_uberon_service.search.return_value = search_result
        
        # Mock the ranking result
        self.agent._rank_terms = MagicMock(return_value={
            "term": self.sample_primitive_heart_term,
            "confidence": 0.95,
            "reasoning": "The query specifically mentions an embryonic heart, which matches the primitive heart term."
        })
        
        # Call the method under test
        result = self.agent.find_term(query)
        
        # Verify the results
        self.assertEqual(result.query, query)
        self.assertEqual(result.total_matches, 2)
        self.assertEqual(result.best_match.id, "UBERON:0004146")
        self.assertEqual(result.best_match.label, "primitive heart")
        self.assertAlmostEqual(result.confidence, 0.95)
        
        # Verify the ranking method was called
        self.agent._rank_terms.assert_called_once_with(
            query, [self.sample_heart_term, self.sample_primitive_heart_term]
        )


if __name__ == "__main__":
    unittest.main() 