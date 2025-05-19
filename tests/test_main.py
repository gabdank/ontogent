"""
Unit tests for the main module.

This module contains tests for verifying the functionality of the main script,
including argument parsing, query processing, and result printing.
"""

import unittest
from unittest.mock import MagicMock, patch, call
import io
import sys
from contextlib import redirect_stdout

from src.main import main, process_query, print_result, run_interactive_mode
from src.models.uberon import SearchResult, UberonTerm


class TestMain(unittest.TestCase):
    """Test cases for the main module."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create sample test data
        self.sample_heart_term = UberonTerm(
            id="UBERON:0000948",
            label="heart",
            definition="A hollow, muscular organ...",
            synonyms=["cardiac muscle"],
            parent_ids=["UBERON:0000077"],
            url="http://purl.obolibrary.org/obo/UBERON_0000948"
        )
        
        # Create a sample search result
        self.sample_result = SearchResult(
            query="heart",
            matches=[self.sample_heart_term],
            total_matches=1,
            best_match=self.sample_heart_term,
            confidence=0.9,
            reasoning="This term directly matches the user's query."
        )
    
    @patch('sys.argv', ['uberon_agent', 'heart', '--log-level', 'DEBUG'])
    @patch('src.main.process_query')
    @patch('src.main.print_result')
    @patch('src.main.setup_logging')
    def test_main_with_cli_args(self, mock_setup_logging, mock_print_result, mock_process_query):
        """Test the main function with command-line arguments."""
        # Set up the mocks
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_process_query.return_value = self.sample_result
        
        # Call the main function
        result = main()
        
        # Verify the result
        self.assertEqual(result, 0)
        
        # Verify the logging setup
        mock_setup_logging.assert_called_once()
        
        # Verify process_query was called with correct arguments
        mock_process_query.assert_called_once_with('heart', mock_logger)
        
        # Verify print_result was called with the result
        mock_print_result.assert_called_once_with(self.sample_result)
    
    @patch('sys.argv', ['uberon_agent'])
    @patch('src.main.run_interactive_mode')
    @patch('src.main.setup_logging')
    def test_main_interactive_mode(self, mock_setup_logging, mock_run_interactive):
        """Test the main function in interactive mode."""
        # Set up the mocks
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_run_interactive.return_value = 0
        
        # Call the main function
        result = main()
        
        # Verify the result
        self.assertEqual(result, 0)
        
        # Verify run_interactive_mode was called
        mock_run_interactive.assert_called_once_with(mock_logger)
    
    @patch('sys.argv', ['uberon_agent', 'heart'])
    @patch('src.main.process_query', side_effect=Exception("Test error"))
    @patch('src.main.setup_logging')
    def test_main_error_handling(self, mock_setup_logging, mock_process_query):
        """Test error handling in the main function."""
        # Set up the mocks
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        
        # Call the main function
        result = main()
        
        # Verify the result indicates error
        self.assertEqual(result, 1)
        
        # Verify the logger was called to log the exception
        mock_logger.exception.assert_called_once()
    
    @patch('src.main.UberonAgent')
    def test_process_query(self, mock_agent_class):
        """Test processing a single query."""
        # Set up the mocks
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        mock_agent.find_term.return_value = self.sample_result
        mock_logger = MagicMock()
        
        # Call the function
        result = process_query("heart", mock_logger)
        
        # Verify the agent was created and used correctly
        mock_agent_class.assert_called_once()
        mock_agent.find_term.assert_called_once_with("heart")
        
        # Verify the logger was used
        mock_logger.info.assert_called()
        
        # Verify the result
        self.assertEqual(result, self.sample_result)
    
    def test_print_result_with_matches(self):
        """Test printing a result with matches."""
        # Capture stdout
        output = io.StringIO()
        
        with redirect_stdout(output):
            print_result(self.sample_result)
        
        # Check the output contains expected information
        output_text = output.getvalue()
        self.assertIn("BEST MATCH:", output_text)
        self.assertIn("UBERON:0000948", output_text)
        self.assertIn("heart", output_text)
        self.assertIn("definition", output_text.lower())
        self.assertIn("cardiac muscle", output_text)
        self.assertIn("confidence", output_text.lower())
    
    def test_print_result_no_matches(self):
        """Test printing a result with no matches."""
        # Create a result with no matches
        no_matches_result = SearchResult(
            query="nonexistent",
            matches=[],
            total_matches=0,
            best_match=None,
            confidence=None,
            reasoning=None
        )
        
        # Capture stdout
        output = io.StringIO()
        
        with redirect_stdout(output):
            print_result(no_matches_result)
        
        # Check the output contains expected information
        output_text = output.getvalue()
        self.assertIn("No matches found", output_text)
        self.assertNotIn("BEST MATCH:", output_text)
    
    @patch('builtins.input', side_effect=['heart', 'quit'])
    @patch('src.main.UberonAgent')
    @patch('src.main.print_result')
    def test_run_interactive_mode(self, mock_print_result, mock_agent_class, mock_input):
        """Test the interactive mode."""
        # Set up the mocks
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        mock_agent.find_term.return_value = self.sample_result
        mock_logger = MagicMock()
        
        # Capture stdout
        output = io.StringIO()
        
        with redirect_stdout(output):
            result = run_interactive_mode(mock_logger)
        
        # Verify the result
        self.assertEqual(result, 0)
        
        # Verify the agent was created and used correctly
        mock_agent_class.assert_called_once()
        mock_agent.find_term.assert_called_once_with("heart")
        
        # Verify print_result was called
        mock_print_result.assert_called_once_with(self.sample_result)
        
        # Check the output contains expected information
        output_text = output.getvalue()
        self.assertIn("Interactive Mode", output_text)
        self.assertIn("Enter a description", output_text)
    
    @patch('builtins.input', side_effect=['', 'heart', 'quit'])
    @patch('src.main.UberonAgent')
    @patch('src.main.print_result')
    def test_run_interactive_mode_empty_input(self, mock_print_result, mock_agent_class, mock_input):
        """Test interactive mode with empty input."""
        # Set up the mocks
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        mock_agent.find_term.return_value = self.sample_result
        mock_logger = MagicMock()
        
        # Run the function
        result = run_interactive_mode(mock_logger)
        
        # Verify the result
        self.assertEqual(result, 0)
        
        # Verify the agent was used only once (skipping the empty input)
        mock_agent.find_term.assert_called_once_with("heart")
    
    @patch('builtins.input', side_effect=Exception("Test error"))
    @patch('src.main.UberonAgent')
    def test_run_interactive_mode_error(self, mock_agent_class, mock_input):
        """Test error handling in interactive mode."""
        # Set up the mocks
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        mock_logger = MagicMock()
        
        # Run the function
        result = run_interactive_mode(mock_logger)
        
        # Verify the result indicates error
        self.assertEqual(result, 1)
        
        # Verify the logger was called to log the exception
        mock_logger.exception.assert_called_once()


if __name__ == "__main__":
    unittest.main() 