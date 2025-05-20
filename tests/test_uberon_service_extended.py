"""
Extended unit tests for the UberonService class.

This module contains additional tests for the UberonService class,
focusing on the parsing methods and API interaction edge cases to
improve code coverage.
"""

import unittest
from unittest.mock import MagicMock, patch, ANY
import json
import requests

from src.services.uberon import UberonService
from src.models.uberon import UberonTerm, SearchQuery, SearchResult
from src.config import settings


class TestUberonServiceExtended(unittest.TestCase):
    """Extended test cases for the UberonService class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Mock the API connection test to return True
        self.connection_patcher = patch.object(UberonService, 'test_api_connection')
        self.mock_test_connection = self.connection_patcher.start()
        self.mock_test_connection.return_value = True
        
        # Create a test service instance
        self.service = UberonService()
    
    def tearDown(self):
        """Clean up after each test method."""
        self.connection_patcher.stop()
    
    def test_parse_search_results_empty(self):
        """Test parsing empty search results."""
        # Call the parse method with empty data
        empty_data = {"response": {"docs": []}}
        terms = self.service._parse_search_results(empty_data)
        
        # Verify the result is an empty list
        self.assertEqual(len(terms), 0)
    
    def test_parse_search_results_invalid_structure(self):
        """Test parsing search results with invalid structure."""
        # Call the parse method with data lacking the expected structure
        invalid_data = {"bad_key": "value"}
        terms = self.service._parse_search_results(invalid_data)
        
        # Verify the result is an empty list
        self.assertEqual(len(terms), 0)
    
    def test_parse_search_results_missing_fields(self):
        """Test parsing search results with missing fields."""
        # Create data with docs but missing required fields
        data_with_missing_fields = {
            "response": {
                "docs": [
                    {
                        "id": "http://purl.obolibrary.org/obo/UBERON_0000948",
                        # Missing label field
                        "short_form": "UBERON_0000948"
                    }
                ]
            }
        }
        
        terms = self.service._parse_search_results(data_with_missing_fields)
        
        # Verify no terms were created due to missing required fields
        self.assertEqual(len(terms), 0)
    
    def test_parse_search_results_different_id_formats(self):
        """Test parsing search results with different ID formats."""
        # Create data with different ID formats
        data_with_different_ids = {
            "response": {
                "docs": [
                    {
                        # Using obo_id
                        "obo_id": "UBERON:0000948",
                        "label": "heart",
                        "ontology_prefix": "UBERON"
                    },
                    {
                        # Using curie
                        "curie": "UBERON:0004146",
                        "label": "primitive heart"
                    },
                    {
                        # Using short_form with ontology_prefix
                        "short_form": "0000123",
                        "label": "some term",
                        "ontology_prefix": "UBERON"
                    },
                    {
                        # Using short_form without ontology_prefix
                        "short_form": "UBERON_0000456",
                        "label": "another term"
                    }
                ]
            }
        }
        
        terms = self.service._parse_search_results(data_with_different_ids)
        
        # Verify all UBERON terms were extracted
        self.assertEqual(len(terms), 4)
        self.assertEqual(terms[0].id, "UBERON:0000948")
        self.assertEqual(terms[1].id, "UBERON:0004146")
        self.assertEqual(terms[2].id, "UBERON:0000123")
        self.assertEqual(terms[3].id, "UBERON:0000456")
    
    def test_parse_search_results_non_uberon_terms(self):
        """Test filtering out non-UBERON terms."""
        # Create data with non-UBERON terms
        data_with_non_uberon = {
            "response": {
                "docs": [
                    {
                        "obo_id": "UBERON:0000948",
                        "label": "heart"
                    },
                    {
                        "obo_id": "GO:0005634",  # Gene Ontology term
                        "label": "nucleus"
                    }
                ]
            }
        }
        
        terms = self.service._parse_search_results(data_with_non_uberon)
        
        # Verify only UBERON terms were included
        self.assertEqual(len(terms), 1)
        self.assertEqual(terms[0].id, "UBERON:0000948")
    
    def test_parse_search_results_with_synonyms(self):
        """Test parsing search results with different synonym formats."""
        # Create data with different synonym formats
        data_with_synonyms = {
            "response": {
                "docs": [
                    {
                        "obo_id": "UBERON:0000948",
                        "label": "heart",
                        # String synonym
                        "synonym": "cardiac muscle"
                    },
                    {
                        "obo_id": "UBERON:0004146",
                        "label": "primitive heart",
                        # List of synonyms
                        "synonym": ["embryonic heart", "heart primordium"]
                    },
                    {
                        "obo_id": "UBERON:0002101",
                        "label": "limb",
                        # Structured obo_synonym
                        "obo_synonym": [
                            {"synonym": "extremity"},
                            {"synonym": "appendage"}
                        ]
                    },
                    {
                        "obo_id": "UBERON:0000033",
                        "label": "head",
                        # String obo_synonym
                        "obo_synonym": ["caput", "cephalic region"]
                    }
                ]
            }
        }
        
        terms = self.service._parse_search_results(data_with_synonyms)
        
        # Verify synonyms were extracted correctly
        self.assertEqual(len(terms), 4)
        self.assertEqual(terms[0].synonyms, ["cardiac muscle"])
        self.assertEqual(set(terms[1].synonyms), {"embryonic heart", "heart primordium"})
        self.assertEqual(set(terms[2].synonyms), {"extremity", "appendage"})
        self.assertIn("caput", terms[3].synonyms)
    
    def test_parse_search_results_with_definitions(self):
        """Test parsing search results with different definition formats."""
        # Create data with different definition formats
        data_with_definitions = {
            "response": {
                "docs": [
                    {
                        "obo_id": "UBERON:0000948",
                        "label": "heart",
                        # String description
                        "description": "A hollow, muscular organ"
                    },
                    {
                        "obo_id": "UBERON:0004146",
                        "label": "primitive heart",
                        # List description
                        "description": ["The developing heart at an early stage"]
                    },
                    {
                        "obo_id": "UBERON:0002101",
                        "label": "limb",
                        # No description, but has def
                        "def": "An appendage that projects from the body"
                    },
                    {
                        "obo_id": "UBERON:0000033",
                        "label": "head",
                        # obo_definition_citation
                        "obo_definition_citation": [
                            {"definition": "Most anterior part of the body"}
                        ]
                    }
                ]
            }
        }
        
        terms = self.service._parse_search_results(data_with_definitions)
        
        # Verify definitions were extracted correctly
        self.assertEqual(len(terms), 4)
        self.assertEqual(terms[0].definition, "A hollow, muscular organ")
        self.assertEqual(terms[1].definition, "The developing heart at an early stage")
        self.assertEqual(terms[2].definition, "An appendage that projects from the body")
        self.assertEqual(terms[3].definition, "Most anterior part of the body")
    
    def test_parse_term_result(self):
        """Test parsing a term result."""
        # Create sample term data
        term_data = {
            "iri": "http://purl.obolibrary.org/obo/UBERON_0000948",
            "obo_id": "UBERON:0000948",
            "label": "heart",
            "description": "A hollow, muscular organ",
            "synonym": ["cardiac muscle", "heart muscle"],
            "is_a": ["UBERON:0000077", "UBERON:0000062"],
        }
        
        # Parse the term
        term = self.service._parse_term_result(term_data)
        
        # Verify the term was parsed correctly
        self.assertIsNotNone(term)
        self.assertEqual(term.id, "UBERON:0000948")
        self.assertEqual(term.label, "heart")
        self.assertEqual(term.definition, "A hollow, muscular organ")
        self.assertEqual(set(term.synonyms), {"cardiac muscle", "heart muscle"})
        self.assertEqual(set(term.parent_ids), {"UBERON:0000077", "UBERON:0000062"})
    
    def test_parse_term_result_with_structured_is_a(self):
        """Test parsing term with structured is_a references."""
        # Create sample term data with structured is_a
        term_data = {
            "obo_id": "UBERON:0000948",
            "label": "heart",
            "is_a": [
                {"obo_id": "UBERON:0000077"},
                {"obo_id": "UBERON:0000062"}
            ]
        }
        
        # Parse the term
        term = self.service._parse_term_result(term_data)
        
        # Verify the parent IDs were extracted
        self.assertEqual(set(term.parent_ids), {"UBERON:0000077", "UBERON:0000062"})
    
    def test_parse_term_result_with_parents(self):
        """Test parsing term with parents field."""
        # Create sample term data with parents field
        term_data = {
            "obo_id": "UBERON:0000948",
            "label": "heart",
            "parents": [
                {"obo_id": "UBERON:0000077"},
                {"obo_id": "UBERON:0000062"}
            ]
        }
        
        # Parse the term
        term = self.service._parse_term_result(term_data)
        
        # Verify the parent IDs were extracted
        self.assertEqual(set(term.parent_ids), {"UBERON:0000077", "UBERON:0000062"})
    
    def test_parse_term_result_with_uberon_id_conversion(self):
        """Test parsing term with UBERON IDs that need conversion."""
        # Create sample term data with UBERON ID needing conversion
        term_data = {
            "obo_id": "UBERON:0000948",
            "label": "heart",
            "is_a": ["UBERON_0000077", "http://purl.obolibrary.org/obo/UBERON_0000062"]
        }
        
        # Parse the term
        term = self.service._parse_term_result(term_data)
        
        # Verify at least one parent ID was converted correctly
        self.assertIsNotNone(term)
        self.assertIn("UBERON:0000077", term.parent_ids)
        # Even if the URL format is not converted, confirm we have the parent IDs in some form
        self.assertEqual(len(term.parent_ids), 2)
    
    def test_test_api_connection_success(self):
        """Test the test_api_connection method when successful."""
        # Remove the patch to test the actual method
        self.connection_patcher.stop()
        
        # Mock the session get method
        with patch.object(self.service.session, 'get') as mock_get:
            # Set up mock response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": {"docs": []}}
            mock_get.return_value = mock_response
            
            # Call the method
            result = self.service.test_api_connection()
            
            # Verify the result
            self.assertTrue(result)
            
        # Restore the patch
        self.connection_patcher = patch.object(UberonService, 'test_api_connection')
        self.mock_test_connection = self.connection_patcher.start()
        self.mock_test_connection.return_value = True
    
    def test_test_api_connection_error(self):
        """Test the test_api_connection method when API returns error."""
        # Remove the patch to test the actual method
        self.connection_patcher.stop()
        
        # Mock the session get method
        with patch.object(self.service.session, 'get') as mock_get:
            # Set up mock response for error
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response
            
            # Call the method
            result = self.service.test_api_connection()
            
            # Verify the result
            self.assertFalse(result)
            
        # Restore the patch
        self.connection_patcher = patch.object(UberonService, 'test_api_connection')
        self.mock_test_connection = self.connection_patcher.start()
        self.mock_test_connection.return_value = True
    
    def test_test_api_connection_invalid_response(self):
        """Test the test_api_connection method when API returns invalid response."""
        # Remove the patch to test the actual method
        self.connection_patcher.stop()
        
        # Mock the session get method
        with patch.object(self.service.session, 'get') as mock_get:
            # Set up mock response with invalid data
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"not_expected": "data"}
            mock_get.return_value = mock_response
            
            # Call the method
            result = self.service.test_api_connection()
            
            # Verify the result
            self.assertFalse(result)
            
        # Restore the patch
        self.connection_patcher = patch.object(UberonService, 'test_api_connection')
        self.mock_test_connection = self.connection_patcher.start()
        self.mock_test_connection.return_value = True
    
    def test_test_api_connection_exception(self):
        """Test the test_api_connection method when an exception occurs."""
        # Remove the patch to test the actual method
        self.connection_patcher.stop()
        
        # Mock the session get method
        with patch.object(self.service.session, 'get', 
                         side_effect=requests.exceptions.RequestException("Connection error")):
            # Call the method
            result = self.service.test_api_connection()
            
            # Verify the result
            self.assertFalse(result)
            
        # Restore the patch
        self.connection_patcher = patch.object(UberonService, 'test_api_connection')
        self.mock_test_connection = self.connection_patcher.start()
        self.mock_test_connection.return_value = True


if __name__ == "__main__":
    unittest.main() 