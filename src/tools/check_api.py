#!/usr/bin/env python3
"""
Utility script to check the Ontobee API status.

This tool helps diagnose connectivity issues with the UBERON API.
"""

import argparse
import json
import sys
import os

# Add the project root to the Python path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, root_dir)

from src.services.uberon import UberonService
from src.utils.logging_utils import setup_logging


def main():
    """
    Check the Ontobee API health and report results.
    """
    parser = argparse.ArgumentParser(description="Check the Ontobee API status")
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Timeout for API requests in seconds (default: 10)"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging()
    
    print("Checking Ontobee API health...")
    health_info = UberonService.check_ontobee_api_health(timeout=args.timeout)
    
    if args.format == "json":
        # Output JSON format
        print(json.dumps(health_info, indent=2))
    else:
        # Output human-readable text
        print("\n=== Ontobee API Health Check ===")
        print(f"Base URL: {health_info['base_url']}")
        print(f"Search endpoint: {health_info['search_endpoint']}")
        print(f"Term endpoint: {health_info['term_endpoint']}")
        print("\nSearch endpoint:")
        print(f"  Accessible: {health_info['search_url_accessible']}")
        if "search_status_code" in health_info:
            print(f"  Status code: {health_info['search_status_code']}")
        if "search_json_valid" in health_info:
            print(f"  Valid JSON: {health_info.get('search_json_valid', False)}")
        if "search_response_valid" in health_info:
            print(f"  Valid structure: {health_info.get('search_response_valid', False)}")
        if "search_response_keys" in health_info:
            print(f"  Response keys: {', '.join(health_info['search_response_keys'])}")
        
        print("\nTerm endpoint:")
        print(f"  Accessible: {health_info['term_url_accessible']}")
        if "term_status_code" in health_info:
            print(f"  Status code: {health_info['term_status_code']}")
        if "term_json_valid" in health_info:
            print(f"  Valid JSON: {health_info.get('term_json_valid', False)}")
        if "term_response_valid" in health_info:
            print(f"  Valid structure: {health_info.get('term_response_valid', False)}")
        if "term_response_keys" in health_info:
            print(f"  Response keys: {', '.join(health_info['term_response_keys'])}")
        
        print("\nSummary:")
        if health_info["error"]:
            print(f"  Error: {health_info['error']}")
        print(f"  Development mode recommended: {health_info['dev_mode_recommended']}")
        print(f"  Recommendation: {health_info['recommendation']}")
        
    # Return success if API is working, failure otherwise
    return 0 if not health_info["dev_mode_recommended"] else 1


if __name__ == "__main__":
    sys.exit(main()) 