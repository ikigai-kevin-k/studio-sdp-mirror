"""
Studio API Service Status Module
Provides functions to query service status from Studio API
"""

import requests
import json
from typing import Optional, Dict, Any
from log_redirector import log_to_file, get_timestamp

# Studio API base URL - Development mode
# Note: This uses port 8084 for service status endpoint
STUDIO_API_BASE_URL = "http://100.64.0.160:8084"


def get_service_status(table_id: str) -> Optional[Dict[str, Any]]:
    """
    Studio API service status endpoint
    GET /v1/service/status?tableId={table_id}
    
    Get service status for a specific table from the Studio API
    
    Args:
        table_id (str): Table ID to query (e.g., "Studio-Roulette-Test", "ARO-001")
        
    Returns:
        Optional[Dict[str, Any]]: Response data if successful, None otherwise
        Response format:
        {
            "error": null,
            "data": {
                "tableId": "Studio-Roulette-Test",
                "uptime": 0,
                "timestamp": 1763685656628,
                "maintenance": true,
                "sdp": "down_pause",
                "idp": "standby",
                "broker": "down",
                "zCam": "down",
                "roulette": "down",
                "shaker": "down",
                "barcodeScanner": "down",
                "nfcScanner": "down"
            }
        }
    """
    # Set up HTTP headers
    headers = {
        "accept": "application/json",
        "x-signature": "rgs-local-signature",
    }
    
    # Build query parameters
    params = {"tableId": table_id}
    
    try:
        # Make GET request to service status endpoint
        response = requests.get(
            f"{STUDIO_API_BASE_URL}/v1/service/status",
            headers=headers,
            params=params,
            verify=False,
            timeout=5,  # 5 second timeout
        )
        
        # Check if the response status code indicates success
        if response.status_code != 200:
            log_to_file(
                f"Service status API error: {response.status_code} - {response.text}",
                "HTTP API >>>"
            )
            return None
        
        # Parse the response JSON
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            log_to_file(
                "Error: Unable to decode JSON response from service status API",
                "HTTP API >>>"
            )
            return None
        
        # Check if there's an error in the response
        if response_data.get("error") is not None:
            log_to_file(
                f"Service status API returned error: {response_data.get('error')}",
                "HTTP API >>>"
            )
            return None
        
        # Return the data portion of the response
        return response_data.get("data")
        
    except requests.exceptions.Timeout:
        log_to_file(
            f"Service status API request timeout for table_id: {table_id}",
            "HTTP API >>>"
        )
        return None
    except requests.exceptions.ConnectionError as e:
        log_to_file(
            f"Service status API connection error for table_id {table_id}: {e}",
            "HTTP API >>>"
        )
        return None
    except Exception as e:
        log_to_file(
            f"Unexpected error calling service status API for table_id {table_id}: {e}",
            "HTTP API >>>"
        )
        return None


def get_sdp_status(table_id: str) -> Optional[str]:
    """
    Get SDP status from service status API
    
    Args:
        table_id (str): Table ID to query
        
    Returns:
        Optional[str]: SDP status string (e.g., "down_pause", "down_cancel", 
                      "up_cancel", "up_resume", "down", "up") or None if error
    """
    status_data = get_service_status(table_id)
    if status_data is None:
        return None
    
    return status_data.get("sdp")


if __name__ == "__main__":
    # Example usage
    print("=== Testing Studio API Service Status Endpoint ===\n")
    
    # Test with example table ID
    test_table_id = "Studio-Roulette-Test"
    print(f"Getting service status for table: {test_table_id}")
    print("-" * 50)
    
    status_data = get_service_status(test_table_id)
    if status_data:
        print(f"✅ Service status retrieved successfully:")
        print(json.dumps(status_data, indent=2))
        
        sdp_status = get_sdp_status(test_table_id)
        if sdp_status:
            print(f"\n✅ SDP Status: {sdp_status}")
    else:
        print("❌ Failed to retrieve service status")
    
    print("\n=== Test completed ===")

