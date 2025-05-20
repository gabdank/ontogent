import pytest
from unittest.mock import patch, MagicMock, call
import subprocess
import json
import sys
import os

# Add the project root to the Python path to allow importing from src
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, root_dir)

from src.tools.check_api import main as check_api_main
from src.tools.check_api import check_ebi_ols4_api_health

# Fixture to mock settings
@pytest.fixture
def mock_settings(mocker):
    mock_api_config = MagicMock()
    mock_api_config.BASE_URL = "http://mock.api.com"
    mock_api_config.SEARCH_ENDPOINT = "/search"
    mock_api_config.TERM_ENDPOINT = "/terms"
    
    mock_settings_obj = MagicMock()
    mock_settings_obj.UBERON_API = mock_api_config
    
    # Patching where settings is defined and imported from
    return mocker.patch('src.config.settings', mock_settings_obj)


# Fixture to mock requests.get
@pytest.fixture
def mock_requests_get(mocker):
    return mocker.patch('requests.Session.get')

# Tests for main()

@patch('src.tools.check_api.check_ebi_ols4_api_health')
def test_main_default_args(mock_check_health, capsys, mock_settings):
    mock_check_health.return_value = {
        'base_url': 'http://mock.api.com',
        'search_endpoint': '/search',
        'term_endpoint': '/terms',
        'search_url_accessible': True,
        'term_url_accessible': True,
        'search_json_valid': True,
        'term_json_valid': True,
        'search_response_valid': True,
        'term_response_valid': True, # This was missing in the original code, needed for term endpoint structure check
        'term_detail_valid': True, # Assuming term detail check passes
        'error': None,
        'api_healthy': True,
        'recommendation': 'API appears to be working correctly.'
    }
    
    with patch.object(sys, 'argv', ['check_api.py']):
        return_code = check_api_main()
        
    captured = capsys.readouterr()
    assert "Checking EBI OLS4 API health..." in captured.out
    assert "=== EBI OLS4 API Health Check ===" in captured.out
    assert "API status: Healthy" in captured.out
    assert return_code == 0
    mock_check_health.assert_called_once_with(timeout=10)

@patch('src.tools.check_api.check_ebi_ols4_api_health')
def test_main_json_format(mock_check_health, capsys, mock_settings):
    mock_result = {
        'base_url': 'http://mock.api.com',
        'search_endpoint': '/search',
        'term_endpoint': '/terms',
        'api_healthy': True
    } # simplified for this test
    mock_check_health.return_value = mock_result
    
    with patch.object(sys, 'argv', ['check_api.py', '--format', 'json']):
        check_api_main()
        
    captured = capsys.readouterr()
    assert "Checking EBI OLS4 API health..." in captured.out
    # Parse the JSON output and check a key
    # The actual JSON output from the script starts after the "Checking..." print
    json_output_str = captured.out.split("Checking EBI OLS4 API health...\n", 1)[1]
    json_output = json.loads(json_output_str)
    assert json_output['api_healthy'] is True
    mock_check_health.assert_called_once_with(timeout=10)

@patch('src.tools.check_api.check_ebi_ols4_api_health')
def test_main_unhealthy(mock_check_health, capsys, mock_settings):
    mock_check_health.return_value = {
        'base_url': 'http://mock.api.com',
        'search_endpoint': '/search',
        'term_endpoint': '/terms',
        'search_url_accessible': False,
        'term_url_accessible': False,
        'error': 'Some error',
        'api_healthy': False,
        'recommendation': 'Fix it.'
    }
    
    with patch.object(sys, 'argv', ['check_api.py']):
        return_code = check_api_main()
        
    captured = capsys.readouterr()
    assert "API status: Unhealthy" in captured.out
    assert "Error: Some error" in captured.out
    assert return_code == 1

def test_main_help(capsys):
    # subprocess.run is used here as argparse with --help exits the process
    # making it hard to capture output directly with pytest tools like capsys
    # when SystemExit is not caught appropriately by the test runner.
    process = subprocess.run(
        [sys.executable, os.path.join(root_dir, 'src/tools/check_api.py'), '--help'],
        capture_output=True,
        text=True,
        check=False # Don't raise exception on non-zero exit for --help
    )
    assert "usage: check_api.py" in process.stdout
    assert "Check the EBI OLS4 API status" in process.stdout
    assert process.returncode == 0

# Tests for check_ebi_ols4_api_health()

def test_check_api_health_healthy(mock_settings, mock_requests_get):
    mock_search_response = MagicMock()
    mock_search_response.status_code = 200
    mock_search_response.json.return_value = {
        "response": {"docs": ["some data"]}
    }
    
    mock_term_response = MagicMock()
    mock_term_response.status_code = 200
    # Simulate EBI OLS4 paginated response for terms list
    mock_term_response.json.return_value = {
        "_links": {"self": { "href": "..."}},
        "page": {"number": 0, "size": 1, "totalPages": 1, "totalElements": 1}
    }

    mock_term_detail_response = MagicMock()
    mock_term_detail_response.status_code = 200
    mock_term_detail_response.json.return_value = {"label": "heart", "iri": "UBERON_0000948"}

    mock_requests_get.side_effect = [mock_search_response, mock_term_response, mock_term_detail_response]
    
    health_info = check_ebi_ols4_api_health(timeout=5)
    
    assert health_info["api_healthy"] is True
    assert health_info["search_url_accessible"] is True
    assert health_info["term_url_accessible"] is True
    assert health_info["search_json_valid"] is True
    assert health_info["term_json_valid"] is True
    assert health_info["search_response_valid"] is True
    assert health_info["term_detail_valid"] is True # Check that term detail was also valid
    assert health_info["recommendation"] == "API appears to be working correctly."
    # Check that the correct URLs were called
    expected_calls = [
        call('http://mock.api.com/search', params={'q': 'heart', 'ontology': 'uberon', 'rows': 1}, timeout=5),
        call('http://mock.api.com/terms/UBERON_0000948', timeout=5),
        call('http://mock.api.com/ontologies/uberon/terms/http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2FUBERON_0000948', timeout=5)
    ]
    mock_requests_get.assert_has_calls(expected_calls)


@pytest.mark.parametrize(
    "search_status, term_status, search_accessible, term_accessible, expected_healthy, recommendation_part",
    [
        (500, 200, False, True, False, "API endpoints are not accessible"),
        (200, 500, True, False, False, "API endpoints are not accessible"),
        (404, 404, False, False, False, "API endpoints are not accessible"),
    ]
)
def test_check_api_health_endpoint_errors(
    mock_settings, mock_requests_get, 
    search_status, term_status, search_accessible, term_accessible, expected_healthy, recommendation_part
):
    mock_search_response = MagicMock()
    mock_search_response.status_code = search_status
    mock_search_response.json.return_value = {"response": {"docs": []}} # Valid structure if accessible
    
    mock_term_response = MagicMock()
    mock_term_response.status_code = term_status
    # Valid structure if accessible, and if the first term check fails, it might not try detail
    mock_term_response.json.return_value = {"_links": {}, "page": {}}

    mock_requests_get.side_effect = [mock_search_response, mock_term_response]
    
    health_info = check_ebi_ols4_api_health(timeout=5)
    
    assert health_info["api_healthy"] is expected_healthy
    assert health_info["search_url_accessible"] is search_accessible
    assert health_info["term_url_accessible"] is term_accessible
    assert recommendation_part in health_info["recommendation"]


@pytest.mark.parametrize(
    "search_json_error, term_json_error, search_valid_json, term_valid_json, recommendation_part",
    [
        (True, False, False, True, "API responses are not valid JSON"),
        (False, True, True, False, "API responses are not valid JSON"),
        (True, True, False, False, "API responses are not valid JSON"),
    ]
)
def test_check_api_health_json_errors(
    mock_settings, mock_requests_get, 
    search_json_error, term_json_error, search_valid_json, term_valid_json, recommendation_part
):
    mock_search_response = MagicMock()
    mock_search_response.status_code = 200
    if search_json_error:
        mock_search_response.json.side_effect = json.JSONDecodeError("err", "doc", 0)
    else:
        mock_search_response.json.return_value = {"response": {"docs": []}}
        
    mock_term_response = MagicMock()
    mock_term_response.status_code = 200
    if term_json_error:
        mock_term_response.json.side_effect = json.JSONDecodeError("err", "doc", 0)
    else:
        mock_term_response.json.return_value = {"_links": {}, "page": {}} # Simplified valid term response

    # We need to provide a mock for the third call (term_detail) as well if the term endpoint itself is fine
    mock_term_detail_response = MagicMock()
    mock_term_detail_response.status_code = 200 
    mock_term_detail_response.json.return_value = {"label": "heart", "iri": "UBERON_0000948"}

    side_effects = [mock_search_response, mock_term_response]
    if not term_json_error: # If term endpoint JSON is fine, it will try the detail endpoint
        side_effects.append(mock_term_detail_response)

    mock_requests_get.side_effect = side_effects
    
    health_info = check_ebi_ols4_api_health(timeout=5)
    
    assert health_info["api_healthy"] is False
    assert health_info["search_json_valid"] is search_valid_json
    assert health_info["term_json_valid"] is term_valid_json
    assert recommendation_part in health_info["recommendation"]


def test_check_api_health_search_response_structure_error(mock_settings, mock_requests_get):
    mock_search_response = MagicMock()
    mock_search_response.status_code = 200
    mock_search_response.json.return_value = {"invalid_key": "data"} # Wrong structure
    
    mock_term_response = MagicMock()
    mock_term_response.status_code = 200
    mock_term_response.json.return_value = {"_links": {}, "page": {}}
    
    mock_term_detail_response = MagicMock()
    mock_term_detail_response.status_code = 200 
    mock_term_detail_response.json.return_value = {"label": "heart", "iri": "UBERON_0000948"}

    mock_requests_get.side_effect = [mock_search_response, mock_term_response, mock_term_detail_response]

    health_info = check_ebi_ols4_api_health(timeout=5)
    
    assert health_info["api_healthy"] is False
    assert health_info["search_response_valid"] is False
    assert "API search response doesn't have the expected structure" in health_info["recommendation"]
    assert health_info["search_response_keys"] == ['invalid_key']

# Test for term response structure error is implicitly covered if 'term_detail_valid' is false
# and the primary term list call is valid but the detail call fails or has wrong structure.
# The current logic for `term_response_valid` in `check_ebi_ols4_api_health` checks the list structure.
# A specific test for `term_response_valid` being false due to term list structure can be added if needed.


@patch('requests.Session.get') # Patching at the source used by the function
def test_check_api_health_request_exception(mock_get, mock_settings):
    import requests # Import requests here for the exception
    mock_get.side_effect = requests.exceptions.RequestException("Connection error")
    
    health_info = check_ebi_ols4_api_health(timeout=5)
    
    assert health_info["api_healthy"] is False
    assert "Request error: Connection error" in health_info["error"]
    assert "Cannot connect to API: Connection error" in health_info["recommendation"]


@patch('requests.Session.get') # Patching at the source used by the function
def test_check_api_health_unexpected_exception(mock_get, mock_settings):
    mock_get.side_effect = Exception("Unexpected issue")
    
    health_info = check_ebi_ols4_api_health(timeout=5)
    
    assert health_info["api_healthy"] is False
    assert "Unexpected error: Unexpected issue" in health_info["error"]
    assert "Error checking API health: Unexpected issue" in health_info["recommendation"] 