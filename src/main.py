"""
Main script for running the UBERON agent.

This script demonstrates usage of the UBERON agent to find suitable
UBERON terms based on user input.
"""

import argparse
import logging
import sys
import os

from src.services.agent import UberonAgent
from src.utils.logging_utils import setup_logging
from src.models.uberon import SearchResult


def main() -> int:
    """
    Main function to run the UBERON agent.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="UBERON Agent: Find suitable UBERON terms for anatomical structures"
    )
    parser.add_argument(
        "query", nargs="?", help="Description of the anatomical structure to search for"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level",
    )
    parser.add_argument(
        "--log-file", help="Path to a log file (if not specified, logs to stderr only)"
    )
    args = parser.parse_args()
    
    # Set up logging
    log_level = getattr(logging, args.log_level)
    logger = setup_logging(log_level=log_level, log_file=args.log_file)
    
    try:
        # If no query is provided, enter interactive mode
        if not args.query:
            return run_interactive_mode(logger)
        
        # Otherwise, process the single query
        result = process_query(args.query, logger)
        print_result(result)
        
        return 0
        
    except Exception as e:
        logger.exception(f"Error running UBERON agent: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1


def run_interactive_mode(logger: logging.Logger) -> int:
    """
    Run the UBERON agent in interactive mode.
    
    Args:
        logger: Logger instance
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.info("Starting UBERON agent in interactive mode")
    print("UBERON Agent - Interactive Mode")
    print("Enter your anatomical structure descriptions, or 'quit' to exit.")
    
    # Create the agent
    try:
        agent = UberonAgent()
        
        while True:
            print("\nEnter a description (or 'quit' to exit):")
            query = input("> ")
            
            if query.lower() in ["quit", "exit", "q"]:
                break
            
            if not query.strip():
                continue
            
            result = agent.find_term(query)
            print_result(result)
            
        return 0
        
    except Exception as e:
        logger.exception(f"Error in interactive mode: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1


def process_query(query: str, logger: logging.Logger) -> SearchResult:
    """
    Process a single query with the UBERON agent.
    
    Args:
        query: Description of the anatomical structure
        logger: Logger instance
        
    Returns:
        SearchResult with matching UBERON terms
    """
    logger.info(f"Processing query: {query}")
    
    agent = UberonAgent()
    result = agent.find_term(query)
    
    logger.info(f"Found {result.total_matches} matches")
    return result


def print_result(result: SearchResult) -> None:
    """
    Print a search result to the console.
    
    Args:
        result: SearchResult to print
    """
    print("\n========== SEARCH RESULTS ==========")
    print(f"Query: {result.query}")
    print(f"Total matches: {result.total_matches}")
    
    if result.best_match:
        print("\nBEST MATCH:")
        print(f"ID: {result.best_match.id}")
        print(f"Label: {result.best_match.label}")
        print(f"Definition: {result.best_match.definition}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Reasoning: {result.reasoning}")
        
        if result.best_match.synonyms:
            print(f"Synonyms: {', '.join(result.best_match.synonyms)}")
        
        if result.best_match.url:
            print(f"URL: {result.best_match.url}")
    
    if len(result.matches) > 1:
        print("\nOTHER MATCHES:")
        for i, term in enumerate(result.matches[1:5], 1):  # Show up to 4 other matches
            print(f"{i}. {term.id}: {term.label}")
    
    if not result.matches:
        print("\nNo matches found. Try a different description.")

    print("====================================")


if __name__ == "__main__":
    sys.exit(main()) 