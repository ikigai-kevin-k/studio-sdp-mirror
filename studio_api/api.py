import requests
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import JsonLexer
import json

# Studio API base URL - Development mode
STUDIO_API_BASE_URL = "http://192.168.20.9:8085"


def healthcheck_get_v1():
    """
    Studio API healthcheck endpoint
    GET /v1/service/healthcheck
    """
    # Set up HTTP headers
    headers = {"accept": "application/json", "x-signature": "secret"}

    # Make GET request to healthcheck endpoint
    response = requests.get(
        f"{STUDIO_API_BASE_URL}/v1/service/healthcheck",
        headers=headers,
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


def table_get_v1(table_ids):
    """
    Studio API table endpoint
    GET /v1/service/table?tableId=ARO-001&tableId=ARO-002&tableId=ARO-001-1

    Args:
        table_ids (list): List of table IDs to query
    """
    # Set up HTTP headers
    headers = {"accept": "application/json", "x-signature": "secret"}

    # Build query parameters for multiple tableIds
    params = {}
    for table_id in table_ids:
        if "tableId" not in params:
            params["tableId"] = []
        params["tableId"].append(table_id)

    # Make GET request to table endpoint
    response = requests.get(
        f"{STUDIO_API_BASE_URL}/v1/service/table",
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


def table_post_v1(table_id, table_status):
    """
    Studio API table endpoint (POST)
    POST /v1/service/table

    Args:
        table_id (str): Table ID to update
        table_status (str): New table status (e.g., "active")
    """
    # Set up HTTP headers
    headers = {
        "accept": "application/json",
        "x-signature": "secret",
        "Content-Type": "application/json",
    }

    # Define payload for the POST request
    data = {"tableId": table_id, "tableStatus": table_status}

    # Make POST request to table endpoint
    response = requests.post(
        f"{STUDIO_API_BASE_URL}/v1/service/table",
        headers=headers,
        json=data,
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


def table_patch_v1(table_id, table_status):
    """
    Studio API table endpoint (PATCH)
    PATCH /v1/service/table

    Args:
        table_id (str): Table ID to update
        table_status (str): New table status (e.g., "inactive")
    """
    # Set up HTTP headers
    headers = {
        "accept": "application/json",
        "x-signature": "secret",
        "Content-Type": "application/json",
    }

    # Define payload for the PATCH request
    data = {"tableId": table_id, "tableStatus": table_status}

    # Make PATCH request to table endpoint
    response = requests.patch(
        f"{STUDIO_API_BASE_URL}/v1/service/table",
        headers=headers,
        json=data,
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
    healthcheck_get_v1()
    table_get_v1(["ARO-001", "ARO-002", "ARO-001-1"])
    table_post_v1("ARO-002-1", "active")
    table_patch_v1("ARO-002-1", "inactive")
