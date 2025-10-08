import requests
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import JsonLexer
import json

# Studio API base URL - Development mode
STUDIO_API_BASE_URL = "http://100.64.0.160:8085"


def device_post_v1(device_id):
    """
    Studio API device endpoint (POST) - Register Device
    POST /v1/service/device
    
    Register a new device with the Studio API
    
    Args:
        device_id (str): Device ID to register (e.g., "ARO-001-1-idp")
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Set up HTTP headers
    headers = {
        "accept": "application/json",
        "x-signature": "rgs-local-signature",
        "Content-Type": "application/json",
    }
    
    # Define payload for the POST request
    data = {"deviceId": device_id}
    
    # Make POST request to device endpoint
    response = requests.post(
        f"{STUDIO_API_BASE_URL}/v1/service/device",
        headers=headers,
        json=data,
        verify=False,
    )
    
    # Check if the response status code indicates success
    if response.status_code not in (200, 201):
        print(f"Error: {response.status_code} - {response.text}")
        return False
    
    try:
        # Parse the response JSON
        response_data = response.json()
        
    except json.JSONDecodeError:
        print("Error: Unable to decode JSON response.")
        return False
    
    # Format the JSON for pretty printing and apply syntax highlighting
    json_str = json.dumps(response_data, indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)
    
    return True


def device_patch_v1(device_id, table_id):
    """
    Studio API device endpoint (PATCH) - Update Device Table Assignment
    PATCH /v1/service/device
    
    Update the table assignment for an existing device
    
    Args:
        device_id (str): Device ID to update (e.g., "ARO-001-1-idp")
        table_id (str): Table ID to assign the device to (e.g., "ARO-001")
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Set up HTTP headers
    headers = {
        "accept": "application/json",
        "x-signature": "rgs-local-signature",
        "Content-Type": "application/json",
    }
    
    # Define payload for the PATCH request
    data = {
        "deviceId": device_id,
        "tableId": table_id
    }
    
    # Make PATCH request to device endpoint
    response = requests.patch(
        f"{STUDIO_API_BASE_URL}/v1/service/device",
        headers=headers,
        json=data,
        verify=False,
    )
    
    # Check if the response status code indicates success
    if response.status_code not in (200, 201):
        print(f"Error: {response.status_code} - {response.text}")
        return False
    
    try:
        # Parse the response JSON
        response_data = response.json()
        
    except json.JSONDecodeError:
        print("Error: Unable to decode JSON response.")
        return False
    
    # Format the JSON for pretty printing and apply syntax highlighting
    json_str = json.dumps(response_data, indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)
    
    return True


def device_get_v1(device_id=None):
    """
    Studio API device endpoint (GET) - Get Device Information
    GET /v1/service/device?deviceId=ARO-001-1-idp
    
    Get device information from the Studio API
    
    Args:
        device_id (str, optional): Device ID to query
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Set up HTTP headers
    headers = {
        "accept": "application/json",
        "x-signature": "rgs-local-signature",
    }
    
    # Build query parameters
    params = {}
    if device_id:
        params["deviceId"] = device_id
    
    # Make GET request to device endpoint
    response = requests.get(
        f"{STUDIO_API_BASE_URL}/v1/service/device",
        headers=headers,
        params=params,
        verify=False,
    )
    
    # Check if the response status code indicates success
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return False
    
    try:
        # Parse the response JSON
        response_data = response.json()
        
    except json.JSONDecodeError:
        print("Error: Unable to decode JSON response.")
        return False
    
    # Format the JSON for pretty printing and apply syntax highlighting
    json_str = json.dumps(response_data, indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)
    
    return True


if __name__ == "__main__":
    # Example usage based on the API documentation
    print("=== Testing Studio API Device Endpoints ===")
    
    # Test device registration (POST)
    print("\n1. Register Device (POST /v1/service/device)")
    print("Registering device: ARO-001-1-idp")
    device_post_v1("ARO-001-1-idp")
    
    # Test device table assignment update (PATCH)
    print("\n2. Update Device Table Assignment (PATCH /v1/service/device)")
    print("Assigning device ARO-001-1-idp to table ARO-001")
    device_patch_v1("ARO-001-1-idp", "ARO-001")
    
    # Test device information retrieval (GET)
    print("\n3. Get Device Information (GET /v1/service/device)")
    print("Getting information for device: ARO-001-1-idp")
    device_get_v1("ARO-001-1-idp")
    
    print("\n=== Test completed ===")
