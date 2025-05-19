"""
Unit tests for the logging_utils module.

This module contains tests for verifying the functionality of the logging utilities,
including log setup, custom error class, and exception decorator.
"""

import unittest
import logging
import io
import sys
import tempfile
import os
from unittest.mock import MagicMock, patch

from src.utils.logging_utils import setup_logging, CustomError, log_exceptions


class TestLoggingUtils(unittest.TestCase):
    """Test cases for the logging utilities."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Store original logger handlers to restore them later
        self.root_logger = logging.getLogger("uberon_agent")
        self.orig_handlers = self.root_logger.handlers.copy()
        self.orig_level = self.root_logger.level
    
    def tearDown(self):
        """Clean up after each test method."""
        # Restore original logger configuration
        self.root_logger.handlers.clear()
        for handler in self.orig_handlers:
            self.root_logger.addHandler(handler)
        self.root_logger.setLevel(self.orig_level)
    
    def test_setup_logging_default(self):
        """Test setting up logging with default parameters."""
        logger = setup_logging()
        
        # Check logger properties
        self.assertEqual(logger.name, "uberon_agent")
        self.assertEqual(logger.level, logging.INFO)
        
        # Check handler configuration
        self.assertEqual(len(logger.handlers), 1)
        handler = logger.handlers[0]
        self.assertIsInstance(handler, logging.StreamHandler)
        self.assertEqual(handler.stream, sys.stdout)
    
    def test_setup_logging_custom_level(self):
        """Test setting up logging with a custom level."""
        logger = setup_logging(log_level=logging.DEBUG)
        
        # Check logger level
        self.assertEqual(logger.level, logging.DEBUG)
    
    def test_setup_logging_with_file(self):
        """Test setting up logging with a log file."""
        # Create a temporary log file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            log_path = temp_file.name
        
        try:
            # Set up logging with the file
            logger = setup_logging(log_file=log_path)
            
            # Check that we have two handlers (console and file)
            self.assertEqual(len(logger.handlers), 2)
            
            # Verify the second handler is a file handler
            file_handler = logger.handlers[1]
            self.assertIsInstance(file_handler, logging.FileHandler)
            
            # Log a message and check if it's in the file
            test_message = "Test log message to file"
            logger.info(test_message)
            
            # Check the file contents
            with open(log_path, 'r') as f:
                log_content = f.read()
                self.assertIn(test_message, log_content)
        
        finally:
            # Clean up the temporary file
            if os.path.exists(log_path):
                os.remove(log_path)
    
    def test_setup_logging_custom_format(self):
        """Test setting up logging with a custom format."""
        custom_format = "%(levelname)s: %(message)s"
        logger = setup_logging(log_format=custom_format)
        
        # Capture log output
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        formatter = logging.Formatter(custom_format)
        handler.setFormatter(formatter)
        
        # Replace the logger's handlers with our test handler
        logger.handlers.clear()
        logger.addHandler(handler)
        
        # Log a message
        logger.info("Test message")
        
        # Check the format of the captured output
        output = stream.getvalue()
        self.assertIn("INFO: Test message", output)
    
    def test_custom_error_basic(self):
        """Test basic functionality of CustomError."""
        # Create a custom error
        error = CustomError("Test error message")
        
        # Check properties
        self.assertEqual(error.message, "Test error message")
        self.assertEqual(str(error), "Test error message")
        self.assertIsInstance(error.context, dict)
        self.assertEqual(len(error.context), 0)
    
    def test_custom_error_with_context(self):
        """Test CustomError with context information."""
        # Create context
        context = {"param1": "value1", "param2": 42}
        
        # Create error with context
        error = CustomError("Test error with context", context)
        
        # Check properties
        self.assertEqual(error.message, "Test error with context")
        self.assertEqual(error.context, context)
        
        # Check string representation includes context
        error_str = str(error)
        self.assertIn("Test error with context", error_str)
        self.assertIn("Context:", error_str)
        self.assertIn("param1: value1", error_str)
        self.assertIn("param2: 42", error_str)
    
    def test_log_exceptions_decorator_success(self):
        """Test the log_exceptions decorator with a successful function call."""
        # Create a test function with the decorator
        mock_logger = MagicMock()
        
        @log_exceptions(mock_logger)
        def test_function(arg1, arg2=None):
            return f"{arg1}-{arg2}"
        
        # Call the function
        result = test_function("hello", arg2="world")
        
        # Verify the function executed normally
        self.assertEqual(result, "hello-world")
        
        # Verify the logger wasn't called
        mock_logger.exception.assert_not_called()
    
    def test_log_exceptions_decorator_error(self):
        """Test the log_exceptions decorator with a failing function."""
        # Create a test function with the decorator
        mock_logger = MagicMock()
        
        @log_exceptions(mock_logger)
        def failing_function():
            raise ValueError("Test error")
        
        # Call the function and expect a CustomError
        with self.assertRaises(CustomError) as context:
            failing_function()
        
        # Verify the logger was called
        mock_logger.exception.assert_called_once()
        
        # Verify the error has the expected attributes
        error = context.exception
        self.assertEqual(error.message, "Test error")
        self.assertIn("function", error.context)
        self.assertEqual(error.context["function"], "failing_function")
    
    def test_log_exceptions_without_logger(self):
        """Test the log_exceptions decorator without providing a logger."""
        # Create a test function with the decorator, without providing a logger
        @log_exceptions()
        def failing_function():
            raise ValueError("Another test error")
        
        # Call the function and expect a CustomError
        with self.assertRaises(CustomError):
            failing_function()
            
        # The test passes if no exception is raised from the decorator itself
    
    def test_log_exceptions_with_args_kwargs(self):
        """Test the log_exceptions decorator preserves args and kwargs in context."""
        mock_logger = MagicMock()
        
        @log_exceptions(mock_logger)
        def complex_function(arg1, arg2, *, kwarg1, kwarg2="default"):
            raise ValueError("Complex error")
        
        # Call the function with various arguments
        with self.assertRaises(CustomError) as context:
            complex_function("value1", "value2", kwarg1="key1", kwarg2="key2")
        
        # Check that the context contains the function arguments
        error = context.exception
        self.assertIn("args", error.context)
        self.assertIn("kwargs", error.context)
        self.assertIn("value1", error.context["args"])
        self.assertIn("value2", error.context["args"])
        self.assertIn("kwarg1", error.context["kwargs"])
        self.assertIn("key1", error.context["kwargs"])
        self.assertIn("kwarg2", error.context["kwargs"])
        self.assertIn("key2", error.context["kwargs"])


if __name__ == "__main__":
    unittest.main() 