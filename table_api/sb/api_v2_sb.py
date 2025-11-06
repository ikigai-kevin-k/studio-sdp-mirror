import requests
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import JsonLexer
import json
import time
import sys
import os

# Add the studio_api directory to Python path to import ErrorMsgId
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from studio_api.ws_err_sig import ErrorMsgId


# CIT SBO-001 - SicBo Game API Module for CIT Environment
# Remove hardcoded accessToken and create a function to get fresh token
def get_access_token():
    """Get a fresh access token from the API for CIT environment"""
    url = "https://crystal-table.iki-cit.cc/v2/service/sessions"
    headers = {
        "accept": "application/json",
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
    }
    data = {"gameCode": "SBO-001", "role": "sdp"}

    try:
        response = requests.post(url, headers=headers, json=data, verify=False)
        if response.status_code == 200:
            response_data = response.json()
            return response_data.get("data", {}).get("token")
        else:
            print(
                f"Error getting token: {response.status_code} - "
                f"{response.text}"
            )
            return None
    except Exception as e:
        print(f"Exception getting token: {e}")
        return None


# Get fresh token
# accessToken = get_access_token()
accessToken = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzZXNzaW9uSWQiOiI2YjY3ZjFiZi03NGI1LTQ0NGQtOWRjOS1hMGViMTI1MjU3NDEiLCJ"
    "nYW1lQ29kZSI6WyJTQk8tMDAxIl0sInJvbGUiOiJzZHAiLCJjcmVhdGVkQXQiOjE3NDg0"
    "MDAxMjQ4MDEsImlhdCI6MTc0ODQwMDEyNH0.wgCKas02lserT3DTA19e4Rv2nyYhj-XRVyZEm"
    "_rEiqQ"
)

if not accessToken:
    print("Failed to get access token. Exiting.")
    exit(1)

print(f"Successfully obtained access token: {accessToken}")


def start_post_v2(url, token):
    """Start a new round for SicBo game"""
    # Set up HTTP headers
    headers = {
        "accept": "application/json",
        "Bearer": f"Bearer {token}",
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={accessToken}",
        "Connection": "close",
        # 'timecode': '26000' # 8 + 15 + 3 = 26
    }

    # Define payload for the POST request
    data = {}
    response = requests.post(
        f"{url}/start", headers=headers, json=data, verify=False
    )

    # Check if the response status code indicates success
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return None, None

    try:
        # Parse the response JSON
        response_data = response.json()

    except json.JSONDecodeError:
        print("Error: Unable to decode JSON response.")
        return None, None

    # Extract roundId from the nested JSON structure
    round_id = (
        response_data.get("data", {})
        .get("table", {})
        .get("tableRound", {})
        .get("roundId")
    )
    betPeriod = response_data.get("data", {}).get("table", {}).get("betPeriod")

    # Handle cases where roundId is not found
    if not round_id:
        print("Error: roundId not found in response.")
        return None, None

    # Format the JSON for pretty printing and apply syntax highlighting
    json_str = json.dumps(response_data, indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

    return round_id, betPeriod


def deal_post_v2(url, token, round_id, result):
    """Deal the result for SicBo game"""
    timecode = str(int(time.time() * 1000))
    headers = {
        "accept": "application/json",
        "Bearer": token,
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "timecode": timecode,
        "Cookie": f"accessToken={accessToken}",
        "Connection": "close",
    }

    data = {
        "roundId": f"{round_id}",
        "sicBo": result,
    }

    response = requests.post(
        f"{url}/deal", headers=headers, json=data, verify=False
    )

    if response.status_code != 200:
        print("====================")
        print("[DEBUG] deal_post_v2")
        print("====================")
        print(f"Error: {response.status_code} - {response.text}")
        print("====================")
        return False

    json_str = json.dumps(response.json(), indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

    print(f"Deal result sent successfully: {result}")
    return True


def finish_post_v2(url, token):
    """Finish the current round for SicBo game"""
    headers = {
        "accept": "application/json",
        "Bearer": token,
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={accessToken}",
        "Connection": "close",
    }
    data = {}
    response = requests.post(
        f"{url}/finish", headers=headers, json=data, verify=False
    )

    if response.status_code != 200:
        print(
            f"Error finishing game: {response.status_code} - {response.text}"
        )
        return False
    json_str = json.dumps(response.json(), indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

    print("Game finished successfully.")
    return True


def visibility_post(url, token, enable):
    """Set table visibility for SicBo game"""
    headers = {
        "accept": "application/json",
        "Bearer": token,
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={accessToken}",
        "Connection": "close",
    }
    print("enable: ", enable)

    visibility = "disabled" if enable is False else "visible"
    data = {"visibility": visibility}

    response = requests.post(
        f"{url}/visibility", headers=headers, json=data, verify=False
    )
    json_str = json.dumps(response.json(), indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)


def get_roundID_v2(url, token):
    """Get current round information for SicBo game"""
    headers = {
        "accept": "application/json",
        "Bearer": f"Bearer {token}",
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={accessToken}",
        "Connection": "close",
    }

    response = requests.get(f"{url}", headers=headers, verify=False)

    # Pretty print API response
    try:
        response_data = response.json()
        print("=== SICBO API Response ===")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print("=== Raw Response (Not JSON) ===")
        print(response.text)
    # Check if the response status code indicates success
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        raise Exception(f"Error: {response.status_code} - {response.text}")

    try:
        # Parse the response JSON
        response_data = response.json()
    except json.JSONDecodeError:
        print("Error: Unable to decode JSON response.")
        raise Exception("Error: Unable to decode JSON response.")

    # Extract roundId from the nested JSON structure
    round_id = (
        response_data.get("data", {})
        .get("table", {})
        .get("tableRound", {})
        .get("roundId")
    )
    status = (
        response_data.get("data", {})
        .get("table", {})
        .get("tableRound", {})
        .get("status")
    )
    betPeriod = response_data.get("data", {}).get("table", {}).get("betPeriod")

    # Handle cases where roundId is not found
    if not round_id:
        print("Error: roundId not found in response.")
        raise Exception("Error: roundId not found in response.")

    return round_id, status, betPeriod


def pause_post_v2(url, token, reason):
    """Pause the current round for SicBo game"""
    headers = {
        "accept": "application/json",
        "Bearer": token,
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={accessToken}",
        "Connection": "close",
    }

    data = {"reason": reason}  # for example: "cannot drive the dice shaker"

    response = requests.post(
        f"{url}/pause", headers=headers, json=data, verify=False
    )
    json_str = json.dumps(response.json(), indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)


def resume_post(url, token):
    """Resume the paused round for SicBo game"""
    headers = {
        "accept": "application/json",
        "Bearer": token,
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={accessToken}",
        "Connection": "close",
    }

    data = {}  # Empty payload as per API specification
    response = requests.post(
        f"{url}/resume", headers=headers, json=data, verify=False
    )
    json_str = json.dumps(response.json(), indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)


def bet_stop_post(url: str, token: str) -> None:
    """
    Stop betting for the current round - SicBo game
    """
    try:
        headers = {
            "accept": "application/json",
            "Bearer": token,
            "x-signature": "los-local-signature",
            "Content-Type": "application/json",
            "Cookie": f"accessToken={accessToken}",
            "Connection": "close",
        }
        data = {}
        response = requests.post(
            f"{url}/bet-stop", headers=headers, json=data, verify=False
        )
        response_data = response.json() if response.text else None

        # Improve error handling
        if response.status_code != 200:
            if response_data:
                error_msg = response_data.get("error", {}).get(
                    "message", "Unknown error"
                )
            else:
                error_msg = f"HTTP {response.status_code}"
            print(f"Error in bet_stop_post: {error_msg}")
            return

        if response_data is None:
            print("Warning: Empty response from server")
            return

        if (
            response_data
            and "error" in response_data
            and response_data["error"]
        ):
            error_msg = response_data["error"].get("message", "Unknown error")
            print(f"Error in bet_stop_post: {error_msg}")
            return

        # Format and display the response
        json_str = json.dumps(response_data, indent=2)
        colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
        print(colored_json)
        print("Successfully stopped betting for the round")

    except requests.exceptions.RequestException as e:
        print(f"Network error in bet_stop_post: {e}")
    except ValueError as e:
        print(f"JSON decode error in bet_stop_post: {e}")
    except Exception as e:
        print(f"Unexpected error in bet_stop_post: {e}")


def cancel_post(url: str, token: str) -> None:
    """
    Cancel the current round - SicBo game
    """
    try:
        headers = {
            "accept": "application/json",
            "Bearer": token,
            "x-signature": "los-local-signature",
            "Content-Type": "application/json",
            "Cookie": f"accessToken={accessToken}",
            "Connection": "close",
        }
        data = {}
        response = requests.post(
            f"{url}/cancel", headers=headers, json=data, verify=False
        )
        response_data = response.json() if response.text else None

        # 改進錯誤處理
        if response.status_code != 200:
            if response_data:
                error_msg = response_data.get("error", {}).get(
                    "message", "Unknown error"
                )
            else:
                error_msg = f"HTTP {response.status_code}"
            print(f"Error in cancel_post: {error_msg}")
            return

        if response_data is None:
            print("Warning: Empty response from server")
            return

        if (
            response_data
            and "error" in response_data
            and response_data["error"]
        ):
            error_msg = response_data["error"].get("message", "Unknown error")
            print(f"Error in cancel_post: {error_msg}")
            return

        print("Successfully cancelled the round")

    except requests.exceptions.RequestException as e:
        print(f"Network error in cancel_post: {e}")
    except ValueError as e:
        print(f"JSON decode error in cancel_post: {e}")
    except Exception as e:
        print(f"Unexpected error in cancel_post: {e}")


def _get_broadcast_metadata(broadcast_type, signal_type="warning"):
    """
    Get ErrorMsgId and metadata for broadcast_type
    
    Args:
        broadcast_type (str): Type of broadcast message (e.g., "dice.reshake")
        signal_type (str): Signal type, 'warning' or 'error' (default: 'warning')
    
    Returns:
        dict: Dictionary containing msgId, content, and metadata
    """
    # Map broadcast_type to ErrorMsgId and metadata
    broadcast_mapping = {
        "dice.reshake": {
            "msgId": ErrorMsgId.SICBO_INVALID_AFTER_RESHAKE.value,
            "content": "Sicbo invalid result after reshake",
            "metadata": {
                "title": "SICBO RESHAKE",
                "description": "Invalid result detected, reshaking dice",
                "code": "SBE.1",
                "suggestion": "Dice will be reshaken shortly",
                "signalType": signal_type,
            },
        },
        "dice.reroll": {
            "msgId": ErrorMsgId.SICBO_INVALID_AFTER_RESHAKE.value,
            "content": "Sicbo invalid result after reshake",
            "metadata": {
                "title": "SICBO RESHAKE",
                "description": "Invalid result detected, reshaking dice",
                "code": "SBE.1",
                "suggestion": "Dice will be reshaken shortly",
                "signalType": signal_type,
            },
        },
        "sicbo.reshake": {
            "msgId": ErrorMsgId.SICBO_INVALID_AFTER_RESHAKE.value,
            "content": "Sicbo invalid result after reshake",
            "metadata": {
                "title": "SICBO RESHAKE",
                "description": "Invalid result detected, reshaking dice",
                "code": "SBE.1",
                "suggestion": "Dice will be reshaken shortly",
                "signalType": signal_type,
            },
        },
        "sicbo.invalid_result": {
            "msgId": ErrorMsgId.SICBO_INVALID_RESULT.value,
            "content": "Sicbo invalid result error",
            "metadata": {
                "title": "SICBO INVALID RESULT",
                "description": "Invalid result detected",
                "code": "SBE.2",
                "suggestion": "Please check the result",
                "signalType": signal_type,
            },
        },
        "sicbo.no_shake": {
            "msgId": ErrorMsgId.SICBO_NO_SHAKE.value,
            "content": "Sicbo no shake error",
            "metadata": {
                "title": "SICBO NO SHAKE",
                "description": "Dice shaker did not shake",
                "code": "SBE.3",
                "suggestion": "Check the shaker mechanism",
                "signalType": signal_type,
            },
        },
        # Add more mappings as needed
    }
    
    # Default mapping if not found
    default_mapping = {
        "msgId": ErrorMsgId.SICBO_INVALID_AFTER_RESHAKE.value,
        "content": f"Broadcast notification: {broadcast_type}",
        "metadata": {
            "title": "BROADCAST NOTIFICATION",
            "description": f"Broadcast message: {broadcast_type}",
            "code": "BRD.1",
            "suggestion": "Please check the game status",
            "signalType": signal_type,
        },
    }
    
    return broadcast_mapping.get(broadcast_type, default_mapping)


def broadcast_post_v2(
    url, token, broadcast_type, audience="players", afterSeconds=20
):
    """
    Send a broadcast message to the SicBo table

    Args:
        url (str): API endpoint URL
        token (str): Authentication token
        broadcast_type (str): Type of broadcast message (e.g., "dice.reshake")
        audience (str): Target audience for the broadcast (default: "players")
        afterSeconds (int): Delay before broadcast (default: 20)
    """
    headers = {
        "accept": "application/json",
        "Bearer": token,
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={accessToken}",
        "Connection": "close",
    }

    # Get ErrorMsgId and metadata based on broadcast_type
    broadcast_data = _get_broadcast_metadata(broadcast_type, signal_type="warning")
    
    # Merge audience and afterSeconds into metadata if needed
    if "metadata" in broadcast_data:
        broadcast_data["metadata"]["audience"] = audience
        broadcast_data["metadata"]["afterSeconds"] = afterSeconds
    
    data = {
        "msgId": broadcast_data["msgId"],
        "content": broadcast_data["content"],
        "metadata": broadcast_data["metadata"],
    }

    response = requests.post(
        f"{url}/broadcast", headers=headers, json=data, verify=False
    )
    json_str = json.dumps(response.json(), indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)


def sdp_config_post(url, token, config_data):
    """
    Update SDP configuration for a specific SicBo table

    Args:
        url (str): API endpoint URL
        token (str): Authentication token
        config_data (dict): Configuration data containing strings and number
    """
    # Modify the URL to use the correct endpoint
    # Remove 'sdp/' from the URL path
    base_url = url.replace("/sdp/table/", "/table/")

    headers = {
        "accept": "application/json",
        "Bearer": token,
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={accessToken}",
        "Connection": "close",
    }

    response = requests.post(
        f"{base_url}/sdp-config",
        headers=headers,
        json=config_data,
        verify=False,
    )

    # Format and display the response
    json_str = json.dumps(response.json(), indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)


def get_sdp_config(url, token):
    """
    Get SDP configuration from the SicBo table status

    Args:
        url (str): API endpoint URL
        token (str): Authentication token

    Returns:
        tuple: (strings, number) from sdpConfig, or (None, None) if not found
    """
    headers = {
        "accept": "application/json",
        "Bearer": f"Bearer {token}",
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={accessToken}",
        "Connection": "close",
    }

    response = requests.get(f"{url}", headers=headers, verify=False)

    if response.status_code != 200:
        return None, None

    try:
        response_data = response.json()
        sdp_config = (
            response_data.get("data", {}).get("table", {}).get("sdpConfig", {})
        )

        strings = sdp_config.get("strings")
        number = sdp_config.get("number")

        return strings, number

    except json.JSONDecodeError:
        print("Error: Unable to decode JSON response.")
        return None, None


def update_sdp_config_from_file(url, token, config_file="sdp.config"):
    """
    Read configuration from sdp.config file and update SDP configuration

    Args:
        url (str): API endpoint URL
        token (str): Authentication token
        config_file (str): Path to the config file

    Returns:
        bool: True if update successful, False otherwise
    """
    try:
        with open(config_file, "r") as f:
            config = json.load(f)

        # Convert the config values to string format for SDP config
        config_data = {
            "strings": json.dumps(
                {
                    "shake_duration": config.get("shake_duration", 8),
                    "result_duration": config.get("result_duration", 12),
                }
            ),
            "number": 0,  # Default value as it's not used for durations
        }

        sdp_config_post(url, token, config_data)
        return True

    except FileNotFoundError:
        print(f"Error: Config file '{config_file}' not found")
        return False
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in config file '{config_file}'")
        return False
    except Exception as e:
        print(f"Error updating SDP config: {str(e)}")
        return False


def cancel_post(url: str, token: str) -> None:
    """
    cancel the current round - SicBo game
    """
    try:
        headers = {
            "accept": "application/json",
            "Bearer": token,
            "x-signature": "los-local-signature",
            "Content-Type": "application/json",
            "Cookie": f"accessToken={accessToken}",
            "Connection": "close",
        }
        data = {}
        response = requests.post(
            f"{url}/cancel", headers=headers, json=data, verify=False
        )
        response_data = response.json() if response.text else None

        # improve error handling
        if response.status_code != 200:
            error_msg = (
                response_data.get("error", {}).get("message", "Unknown error")
                if response_data
                else f"HTTP {response.status_code}"
            )
            print(f"Error in cancel_post: {error_msg}")
            return

        if response_data is None:
            print("Warning: Empty response from server")
            return

        if "error" in response_data:
            error_msg = response_data["error"].get("message", "Unknown error")
            print(f"Error in cancel_post: {error_msg}")
            return

        print("Successfully cancelled the round")

    except requests.exceptions.RequestException as e:
        print(f"Network error in cancel_post: {e}")
    except ValueError as e:
        print(f"JSON decode error in cancel_post: {e}")
    except Exception as e:
        print(f"Unexpected error in cancel_post: {e}")


def broadcast_post_v2(
    url, token, broadcast_type, audience="players", afterSeconds=20
):  # , metadata=None):
    """
    Send a broadcast message to the table

    Args:
        url (str): API endpoint URL
        token (str): Authentication token
        broadcast_type (str): Type of broadcast message (e.g., "dice.reroll")
        audience (str): Target audience for the broadcast (default: "players")
        metadata (dict): Additional metadata for the broadcast (default: None)
    """
    headers = {
        "accept": "application/json",
        "Bearer": token,
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={accessToken}",
        "Connection": "close",
    }

    # Get ErrorMsgId and metadata based on broadcast_type
    broadcast_data = _get_broadcast_metadata(broadcast_type, signal_type="warning")
    
    # Merge audience and afterSeconds into metadata if needed
    if "metadata" in broadcast_data:
        broadcast_data["metadata"]["audience"] = audience
        broadcast_data["metadata"]["afterSeconds"] = afterSeconds
    
    data = {
        "msgId": broadcast_data["msgId"],
        "content": broadcast_data["content"],
        "metadata": broadcast_data["metadata"],
    }

    response = requests.post(
        f"{url}/broadcast", headers=headers, json=data, verify=False
    )
    json_str = json.dumps(response.json(), indent=2)

    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)


if __name__ == "__main__":
    cnt = 0
    while cnt < 1:
        # SicBo game results - three dice values
        results = [1, 2, 3]  # Example dice results
        # CIT environment URLs
        get_url = "https://crystal-table.iki-cit.cc/v2/service/tables/"
        post_url = "https://crystal-table.iki-cit.cc/v2/service/tables/"

        # SicBo game code for CIT environment
        gameCode = "SBO-001"
        get_url = get_url + gameCode
        post_url = post_url + gameCode
        token = "E5LN4END9Q"

        # broadcast_post(post_url, token, "roulette.relaunch", "players", 20)
        # broadcast_post(post_url, token, "dice.reshake", "sdp", 20)
        print("================Start================\n")
        round_id, betPeriod = start_post_v2(post_url, token)
        round_id, status, betPeriod = get_roundID_v2(get_url, token)
        print(round_id, status, betPeriod)

        # print(round_id, status, betPeriod)
        # while betPeriod >= 0: #or status !='bet-stopped':
        # print("Bet Period count down:", betPeriod)
        # betPeriod = betPeriod - 1
        # _, status, _ =  get_roundID(get_url, token)

        # print("================Pause================\n")
        # pause_post(post_url, token, "test")

        # print("================Resume================\n")
        # resume_post(post_url, token)

        # print("================Invisibility================\n")
        # visibility_post(post_url, token, False)

        # print("================Visibility================\n")
        # visibility_post(post_url, token, True)
        print("================Bet Stop================\n")
        time.sleep(13)  # Wait for betting period
        bet_stop_post(post_url, token)
        print("================Deal================\n")
        # time.sleep(10)
        deal_post_v2(post_url, token, round_id, results)
        print("================Finish================\n")
        finish_post_v2(post_url, token)

        # print("================Cancel================\n")
        # cancel_post(post_url, token)

        # Add example usage
        # config_data = {
        #     "shake_duration": 7,
        #     "result_duration": 4
        # }
        # sdp_config_post(sdp_url, token, config_data)

        # Example usage of get_sdp_config
        # strings, number = get_sdp_config(get_url, token)
        # print(f"SDP Config - strings: {strings}, number: {number}")

        cnt += 1
