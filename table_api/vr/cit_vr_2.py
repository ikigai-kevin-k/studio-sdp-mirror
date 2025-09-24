import requests
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import JsonLexer
import json
import time
import os


# Load configuration from JSON file
def load_config():
    """Load configuration from vr-2-test.json"""
    config_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "conf",
        "vr-2-test.json",
    )
    try:
        with open(config_path, "r") as f:
            configs = json.load(f)
            # Find CIT-2 configuration
            for config in configs:
                if config["name"] == "CIT-2":
                    return config
        raise Exception("CIT-2 configuration not found in config file")
    except Exception as e:
        print(f"Error loading config: {e}")
        return None


# Load CIT-2 configuration
config = load_config()
if config:
    accessToken = config["access_token"]
    gameCode = config["game_code"]
    get_url = config["get_url"] + gameCode
    post_url = config["post_url"] + gameCode
    token = config["table_token"]
else:
    # Fallback to hardcoded values if config loading fails
    accessToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZXNzaW9uSWQiOiJhNDkwZTNlZC0yMjc2LTRmMGQtYWRkNy04ZTk5MjA5MjViYjMiLCJnYW1lQ29kZSI6WyJBUk8tMDAyLTIiXSwicm9sZSI6InNkcCIsImNyZWF0ZWRBdCI6MTc1ODY5NTczNDA3MCwiaWF0IjoxNzU4Njk1NzM0fQ.MhzfWkwcfGyQ-q_Rj2KbFFvF5mY9gPb2mQB3IzlmCww"
    gameCode = "ARO-002-2"
    get_url = "https://crystal-table.iki-cit.cc/v2/service/tables/" + gameCode
    post_url = "https://crystal-table.iki-cit.cc/v2/service/tables/" + gameCode
    token = "E5LN4END9Q"


def start_post_v2(url, token):
    """Start a new round for Speed Roulette game"""
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

    # Parse response for better error handling
    try:
        response_data = response.json() if response.text else None
    except (ValueError, json.JSONDecodeError):
        response_data = None

    # Check if the response status code indicates success
    if response.status_code != 200:
        if response_data and isinstance(response_data, dict):
            error_msg = response_data.get("error", {}).get("message", "Unknown error")
            print(f"Error: {response.status_code} - {error_msg}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
        return None, None

    if not response_data:
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
    """Deal the result for Speed Roulette game"""
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
        "roulette": result,
    }

    response = requests.post(
        f"{url}/deal", headers=headers, json=data, verify=False
    )
    
    # Parse response for better error handling
    try:
        response_data = response.json() if response.text else None
    except (ValueError, json.JSONDecodeError):
        response_data = None
    
    if response.status_code != 200:
        print("====================")
        print("[DEBUG] deal_post_v2")
        print("====================")
        if response_data and isinstance(response_data, dict):
            error_msg = response_data.get("error", {}).get("message", "Unknown error")
            print(f"Error: {response.status_code} - {error_msg}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
        print("====================")
        return False

    # Display response
    if response_data and isinstance(response_data, dict):
        json_str = json.dumps(response_data, indent=2)
        colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
        print(colored_json)
    else:
        print("Response data:", response_data)

    print(f"Deal result sent successfully: {result}")
    return True


def finish_post_v2(url, token):
    """Finish the current round for Speed Roulette game"""
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

    # Parse response for better error handling
    try:
        response_data = response.json() if response.text else None
    except (ValueError, json.JSONDecodeError):
        response_data = None

    if response.status_code != 200:
        if response_data and isinstance(response_data, dict):
            error_msg = response_data.get("error", {}).get("message", "Unknown error")
            print(f"Error finishing game: {response.status_code} - {error_msg}")
        else:
            print(f"Error finishing game: {response.status_code} - {response.text}")
        return False
    
    # Display response
    if response_data and isinstance(response_data, dict):
        json_str = json.dumps(response_data, indent=2)
        colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
        print(colored_json)
    else:
        print("Response data:", response_data)

    print("Game finished successfully.")
    return True


def visibility_post(url, token, enable):
    """Set table visibility for Speed Roulette game"""
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


def get_roundID(url, token):
    """Get current round information for Speed Roulette game"""
    headers = {
        "accept": "application/json",
        "Bearer": f"Bearer {token}",
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={accessToken}",
    }

    response = requests.get(f"{url}", headers=headers, verify=False)

    # Pretty print API response
    try:
        response_data = response.json()
        print("=== Speed Roulette API Response ===")
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


def pause_post(url, token, reason):
    """Pause the current round for Speed Roulette game"""
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
    """Resume the paused round for Speed Roulette game"""
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

    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)


def sdp_config_post(url, token, config_data):
    """
    Update SDP configuration for a specific Speed Roulette table

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
    Get SDP configuration from the Speed Roulette table status

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
    cancel the current round - Speed Roulette game
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
        try:
            response_data = response.json() if response.text else None
        except (ValueError, json.JSONDecodeError):
            response_data = None

        # improve error handling
        if response.status_code != 200:
            error_msg = (
                response_data.get("error", {}).get("message", "Unknown error")
                if response_data and isinstance(response_data, dict)
                else f"HTTP {response.status_code}"
            )
            print(f"Error in cancel_post: {error_msg}")
            return

        if response_data is None:
            print("Warning: Empty response from server")
            return

        if response_data and isinstance(response_data, dict) and "error" in response_data:
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


def bet_stop_post(url: str, token: str) -> bool:
    """
    Stop betting for the current round - Speed Roulette game
    Returns True if successful, False otherwise
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
        try:
            response_data = response.json() if response.text else None
        except (ValueError, json.JSONDecodeError):
            response_data = None

        # Improve error handling
        if response.status_code != 200:
            if response_data and isinstance(response_data, dict):
                error_msg = response_data.get("error", {}).get(
                    "message", "Unknown error"
                )
            else:
                error_msg = f"HTTP {response.status_code}"
            print(f"Error in bet_stop_post: {error_msg}")
            return False

        if response_data is None:
            print("Warning: Empty response from server")
            return False

        if (
            response_data
            and isinstance(response_data, dict)
            and "error" in response_data
            and response_data["error"]
        ):
            error_msg = response_data["error"].get("message", "Unknown error")
            print(f"Error in bet_stop_post: {error_msg}")
            return False

        # Format and display the response
        if response_data and isinstance(response_data, dict):
            json_str = json.dumps(response_data, indent=2)
            colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
            print(colored_json)
        else:
            print("Response data:", response_data)
        print("Successfully stopped betting for the round")
        return True

    except requests.exceptions.RequestException as e:
        print(f"Network error in bet_stop_post: {e}")
        return False
    except ValueError as e:
        print(f"JSON decode error in bet_stop_post: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error in bet_stop_post: {e}")
        return False


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

    # Generate a unique message ID using timestamp
    msg_id = f"msg_{int(time.time() * 1000)}"

    data = {
        "msgId": msg_id,
        # "type": broadcast_type,
        # "audience": audience,
        "metadata": {
            "type": broadcast_type,
            "audience": audience,
            "afterSeconds": afterSeconds,
        },  # metadata or {}
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
        results = "2"  # str(random.randint(0, 36))
        # URLs and tokens are now loaded from config file at module level

        # broadcast_post(post_url, token, "roulette.relaunch", "players", 20)
        print("================Start================\n")
        round_id, betPeriod = start_post_v2(post_url, token)
        round_id, status, betPeriod = get_roundID(get_url, token)
        print(round_id, status, betPeriod)

        # betPeriod = 19
        # print(round_id, status, betPeriod)
        # while betPeriod > 0: #or status !='bet-stopped':
        #     print("Bet Period count down:", betPeriod)
        #     time.sleep(1)
        #     betPeriod = betPeriod - 1
        #     _, status, _ =  get_roundID(get_url, token)
        #     print(status)

        # print("================Pause================\n")
        # pause_post(post_url, token, "test")
        # time.sleep(1)

        # print("================Resume================\n")
        # resume_post(post_url, token)
        # time.sleep(1)

        # print("================Invisibility================\n")
        # visibility_post(post_url, token, False)
        # time.sleep(1)

        # print("================Visibility================\n")
        # visibility_post(post_url, token, True)
        # time.sleep(1)

        print("================Deal================\n")
        time.sleep(18)
        bet_stop_post(post_url, token)
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
