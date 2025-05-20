#!/usr/bin/env python3
"""
Utility script to check the EBI OLS4 API status.

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
    Check the EBI OLS4 API health and report results.
    """
    parser = argparse.ArgumentParser(description="Check the EBI OLS4 API status")
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
    
    print("Checking EBI OLS4 API health...")
    health_info = check_ebi_ols4_api_health(timeout=args.timeout)
    
    if args.format == "json":
        # Output JSON format
        print(json.dumps(health_info, indent=2))
    else:
        # Output human-readable text
        print("\n=== EBI OLS4 API Health Check ===")
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
        print(f"  API status: {'Healthy' if health_info['api_healthy'] else 'Unhealthy'}")
        print(f"  Recommendation: {health_info['recommendation']}")
        
    # Return success if API is working, failure otherwise
    return 0 if health_info["api_healthy"] else 1


def check_ebi_ols4_api_health(timeout: int = 10) -> dict:
    """
    Check the health of the EBI OLS4 API.
    
    This function tests the connectivity and response structure of the EBI OLS4 API.
    
    Args:
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary with API health information
    """
    import requests
    import time
    from src.config import settings
    
    api_config = settings.UBERON_API
    
    base_url = api_config.BASE_URL
    search_endpoint = api_config.SEARCH_ENDPOINT
    term_endpoint = api_config.TERM_ENDPOINT
    
    search_url = f"{base_url}{search_endpoint}"
    term_url = f"{base_url}{term_endpoint}"
    
    health_info = {
        "base_url": base_url,
        "search_endpoint": search_endpoint,
        "term_endpoint": term_endpoint,
        "search_url_accessible": False,
        "term_url_accessible": False,
        "search_response_valid": False,
        "term_response_valid": False,
        "error": None,
        "api_healthy": False,
        "timestamp": time.time()
    }
    
    session = requests.Session()
    
    try:
        # Test search endpoint
        params = {
            "q": "heart",
            "ontology": "uberon",
            "rows": 1
        }
        
        search_response = session.get(search_url, params=params, timeout=timeout)
        health_info["search_url_accessible"] = search_response.status_code == 200
        health_info["search_status_code"] = search_response.status_code
        
        if health_info["search_url_accessible"]:
            # Check if response is valid JSON
            try:
                search_data = search_response.json()
                health_info["search_json_valid"] = True
                
                # Check if response has expected structure
                if "response" in search_data and "docs" in search_data["response"]:
                    health_info["search_response_valid"] = True
                else:
                    health_info["search_response_keys"] = list(search_data.keys())
            except Exception as e:
                health_info["search_json_valid"] = False
                health_info["search_parse_error"] = str(e)
        
        # Test term endpoint with a known term ID
        term_request_url = f"{term_url}/UBERON_0000948"  # Heart ID
        
        term_response = session.get(term_request_url, timeout=timeout)
        health_info["term_url_accessible"] = term_response.status_code == 200
        health_info["term_status_code"] = term_response.status_code
        
        if health_info["term_url_accessible"]:
            # Check if response is valid JSON
            try:
                term_data = term_response.json()
                health_info["term_json_valid"] = True
                
                # Check if response has expected structure
                # EBI OLS4 API returns a collection of terms with pagination
                if "_links" in term_data and "page" in term_data:
                    # This appears to be a paginated response of terms
                    health_info["term_response_valid"] = True
                    # Get a specific term - we need to use a different endpoint
                    term_detail_url = f"{base_url}/ontologies/uberon/terms/http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2FUBERON_0000948"
                    try:
                        term_detail_response = session.get(term_detail_url, timeout=timeout)
                        if term_detail_response.status_code == 200:
                            term_detail = term_detail_response.json()
                            if "label" in term_detail and "iri" in term_detail:
                                health_info["term_detail_valid"] = True
                    except Exception:
                        # Ignore errors in the second check
                        pass
                else:
                    health_info["term_response_keys"] = list(term_data.keys())
            except Exception as e:
                health_info["term_json_valid"] = False
                health_info["term_parse_error"] = str(e)
        
        # Determine if API is healthy
        if not health_info["search_url_accessible"] or not health_info["term_url_accessible"]:
            health_info["api_healthy"] = False
            health_info["recommendation"] = "API endpoints are not accessible. Check your network connection and try again. If the issue persists, the EBI OLS4 API may be experiencing downtime."
        elif not health_info["search_json_valid"] or not health_info["term_json_valid"]:
            health_info["api_healthy"] = False
            health_info["recommendation"] = "API responses are not valid JSON. The EBI OLS4 API may have changed its response format or is returning errors."
        elif not health_info["search_response_valid"]:
            health_info["api_healthy"] = False
            health_info["recommendation"] = "API search response doesn't have the expected structure. The EBI OLS4 API may have changed its response format."
        else:
            health_info["api_healthy"] = True
            health_info["recommendation"] = "API appears to be working correctly."
            
    except requests.exceptions.RequestException as e:
        health_info["error"] = f"Request error: {str(e)}"
        health_info["api_healthy"] = False
        health_info["recommendation"] = f"Cannot connect to API: {str(e)}. Check your network connection and API endpoint configuration."
    except Exception as e:
        health_info["error"] = f"Unexpected error: {str(e)}"
        health_info["api_healthy"] = False
        health_info["recommendation"] = f"Error checking API health: {str(e)}. Please report this issue."
    
    return health_info


if __name__ == "__main__":
    sys.exit(main()) 