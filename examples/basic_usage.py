#!/usr/bin/env python3
"""
Basic usage example for the Ontogent agent.

This script demonstrates how to initialize and use the Ontogent agent
to find UBERON terms for anatomical structures.
"""

from src.services.agent import UberonAgent

def main():
    # Initialize the agent
    # This will automatically use the ANTHROPIC_API_KEY environment variable
    print("Initializing Ontogent agent...")
    agent = UberonAgent()
    
    # Example 1: Search for a simple term
    query = "heart"
    print(f"\nExample 1: Searching for '{query}'")
    result = agent.find_term(query)
    print_result(result)
    
    # Example 2: Search for a more specific term
    query = "embryonic heart"
    print(f"\nExample 2: Searching for '{query}'")
    result = agent.find_term(query)
    print_result(result)
    
    # Example 3: Search for a term with species information
    query = "mouse liver"
    print(f"\nExample 3: Searching for '{query}'")
    result = agent.find_term(query)
    print_result(result)

def print_result(result):
    """Print the search result in a readable format."""
    print(f"Found {result.total_matches} matches.")
    
    if result.best_match:
        print("\nBest match:")
        print(f"  ID: {result.best_match.id}")
        print(f"  Label: {result.best_match.label}")
        print(f"  Definition: {result.best_match.definition}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Reasoning: {result.reasoning}")
    else:
        print("No matches found.")

if __name__ == "__main__":
    main() 