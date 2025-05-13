#!/usr/bin/env python3
"""
Test that the environment is properly set up.

This script imports the key components of the Ontogent package
to verify that the conda environment and package installation
are working correctly.
"""

import sys

def test_imports():
    """Test that all required packages can be imported."""
    try:
        # Basic Python packages
        import json
        import logging
        
        # External dependencies
        import anthropic
        import pydantic
        import requests
        import dotenv
        
        # Ontogent package
        from src.config import settings
        from src.models.uberon import UberonTerm
        from src.services.agent import UberonAgent
        from src.services.llm import LLMService
        from src.services.uberon import UberonService
        from src.utils.logging_utils import setup_logging
        
        print("✅ All imports successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


if __name__ == "__main__":
    print("Testing Ontogent environment setup...")
    success = test_imports()
    
    if success:
        print("\nEnvironment is correctly set up! 🎉")
        print("\nTo use Ontogent, make sure to set your Anthropic API key:")
        print("export ANTHROPIC_API_KEY='your_api_key_here'")
    else:
        print("\nEnvironment setup is incomplete. Please check the error messages above.")
    
    sys.exit(0 if success else 1) 