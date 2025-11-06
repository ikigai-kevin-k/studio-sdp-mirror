import requests
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import JsonLexer
import json
import time
import os
import sys

# Import ErrorMsgId from ws_err_sig
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "studio_api"))
try:
    from studio_api.ws_err_sig import ErrorMsgId
except ImportError:
    # Fallback if import fails
    from enum import Enum
    class ErrorMsgId(Enum):
        ROULETTE_INVALID_AFTER_RELAUNCH = "ROULETTE_INVALID_AFTER_RELAUNCH"
        ROULETTE_NO_BALL_DETECT = "ROULETTE_NO_BALL_DETECT"
        ROULETTE_NO_WIN_NUM = "ROULETTE_NO_WIN_NUM"
        ROULETTE_NO_REACH_POS = "ROULETTE_NO_REACH_POS"
        ROULETTE_SENSOR_STUCK = "ROULETTE_SENSOR_STUCK"
        ROUELTTE_WRONG_BALL_DIR = "ROUELTTE_WRONG_BALL_DIR"
        ROULETTE_LAUNCH_FAIL = "ROULETTE_LAUNCH_FAIL"


# Load configuration from JSON file
def load_config():
    """Load configuration from sr-1.json"""
    config_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "conf",
        "sr-1.json",
    )
    try:
        with open(config_path, "r") as f:
            configs = json.load(f)
            # Find PRD-7 configuration
            for config in configs:
                if config["name"] == "PRD-7":
                    return config
        raise Exception("PRD configuration not found in config file")
    except Exception as e:
        print(f"Error loading config: {e}")
        return None


# Load PRD configuration
config = load_config()
if config:
    accessToken = config["access_token"]
    gameCode = config["game_code"]
    get_url = config["get_url"] + gameCode
    post_url = config["post_url"] + gameCode
    token = config["table_token"]
else:
    # Fallback to hardcoded values if config loading fails
    accessToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZXNzaW9uSWQiOiIwYTg4YTNlYy1lZTcwLTRiZWMtYWI4MC1iMzI2ZjUxNzg5M2YiLCJnYW1lQ29kZSI6WyJBUk8tMDA3Il0sInJvbGUiOiJzZHAiLCJjcmVhdGVkQXQiOjE3NjA0MzIxMjEwNDcsImlhdCI6MTc2MDQzMjEyMX0.rhaH2ecg4vtPF3j85hCV2JCTn9KwM-2bbvNbyUn59mM"
    gameCode = "ARO-007"
    get_url = "https://crystal-table.ikg-game.cc/v2/service/tables/" + gameCode
    post_url = (
        "https://crystal-table.ikg-game.cc/v2/service/tables/" + gameCode
    )
    token = "E5LN4END9Q"


def start_post_v2_prd(url, token):
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
        return -1, -1

    try:
        # Parse the response JSON
        response_data = response.json()

    except json.JSONDecodeError:
        print("Error: Unable to decode JSON response.")
        return -1, -1

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
        return -1, -1

    # Format the JSON for pretty printing and apply syntax highlighting
    json_str = json.dumps(response_data, indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

    return round_id, betPeriod


def deal_post_v2_prd(url, token, round_id, result):
    timecode = str(int(time.time() * 1000) + 5000)
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
        "roulette": result,  # 修改: 使用 "roulette" 而不是 "sicBo"，直接傳入數字的string
    }

    response = requests.post(
        f"{url}/deal", headers=headers, json=data, verify=False
    )
    json_str = json.dumps(response.json(), indent=2)

    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)


def finish_post_v2_prd(url, token):
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
    json_str = json.dumps(response.json(), indent=2)

    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)


def visibility_post_v2_prd(url, token, enable):
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
    # print("vis: ", visibility)
    data = {"visibility": visibility}

    response = requests.post(
        f"{url}/visibility", headers=headers, json=data, verify=False
    )
    json_str = json.dumps(response.json(), indent=2)

    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)


def get_roundID_v2_prd(url, token):
    # Set up HTTP headers

    # print("URL:", url)

    headers = {
        "accept": "application/json",
        "Bearer": f"Bearer {token}",
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={accessToken}",
        "Connection": "close",
    }

    # Define payload for the POST request
    data = {}
    response = requests.get(f"{url}", headers=headers, verify=False)

    # Check if the response status code indicates success
    if response.status_code != 200:
        # print(f"Error: {response.status_code} - {response.text}")
        return -1, -1, -1

    try:
        # Parse the response JSON
        response_data = response.json()
    except json.JSONDecodeError:
        print("Error: Unable to decode JSON response.")
        return -1, -1, -1

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
        return -1, -1, -1

    # Format the JSON for pretty printing and apply syntax highlighting
    json_str = json.dumps(response_data, indent=2)
    # colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    # print(colored_json)

    return round_id, status, betPeriod


def pause_post_v2_prd(url, token, reason):
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


def resume_post_v2_prd(url, token):
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


def sdp_config_post_v2_prd(url, token, config_data):
    """
    Update SDP configuration for a specific table

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


def get_sdp_config_v2_prd(url, token):
    """
    Get SDP configuration from the table status

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


def update_sdp_config_from_file_v2_prd(url, token, config_file="sdp.config"):
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

        # sdp_config_post(url, token, config_data)
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


def cancel_post_v2_prd(url: str, token: str) -> None:
    """
    取消當前局次
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


def bet_stop_post_prd(url: str, token: str) -> bool:
    """
    Stop betting for the current round - Speed Roulette game (PRD environment)
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
        response_data = response.json() if response.text else None

        # Improve error handling
        if response.status_code != 200:
            if response_data:
                error_msg = response_data.get("error", {}).get(
                    "message", "Unknown error"
                )
            else:
                error_msg = f"HTTP {response.status_code}"
            print(f"Error in bet_stop_post_prd: {error_msg}")
            return False

        if response_data is None:
            print("Warning: Empty response from server")
            return False

        if (
            response_data
            and "error" in response_data
            and response_data["error"]
        ):
            error_msg = response_data["error"].get("message", "Unknown error")
            print(f"Error in bet_stop_post_prd: {error_msg}")
            return False

        # Format and display the response
        json_str = json.dumps(response_data, indent=2)
        colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
        print(colored_json)
        print("Successfully stopped betting for the round")
        return True

    except requests.exceptions.RequestException as e:
        print(f"Network error in bet_stop_post_prd: {e}")
        return False
    except ValueError as e:
        print(f"JSON decode error in bet_stop_post_prd: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error in bet_stop_post_prd: {e}")
        return False


def _get_broadcast_metadata_prd(broadcast_type, signal_type="warning"):
    """
    Get ErrorMsgId and metadata for broadcast_type
    
    Args:
        broadcast_type (str): Type of broadcast message (e.g., "roulette.relaunch")
        signal_type (str): Signal type, 'warning' or 'error' (default: 'warning')
    
    Returns:
        tuple: (ErrorMsgId value, metadata dict)
    """
    # Map broadcast_type to ErrorMsgId and metadata
    broadcast_mapping = {
        "roulette.relaunch": {
            "msgId": ErrorMsgId.ROULETTE_INVALID_AFTER_RELAUNCH.value,
            "content": "Roulette relaunch notification",
            "metadata": {
                "title": "ROULETTE RELAUNCH",
                "description": "Roulette game relaunch notification",
                "code": "ARE.1",
                "suggestion": "Game will relaunch shortly",
                "signalType": signal_type,
            },
        },
        "roulette.launch_fail": {
            "msgId": ErrorMsgId.ROULETTE_LAUNCH_FAIL.value,
            "content": "Roulette launch fail error",
            "metadata": {
                "title": "ROULETTE LAUNCH FAIL",
                "description": "Roulette ball launch failed",
                "code": "ARE.2",
                "suggestion": "Check the launch mechanism",
                "signalType": signal_type,
            },
        },
        "roulette.wrong_ball_dir": {
            "msgId": ErrorMsgId.ROUELTTE_WRONG_BALL_DIR.value,
            "content": "Roulette wrong ball direction error",
            "metadata": {
                "title": "WRONG BALL DIRECTION",
                "description": "Ball is recognized spinning toward the wrong direction in the rim",
                "code": "ARE.4",
                "suggestion": "Check the sensor, it usually is due to sensor mis-recognize the direction",
                "signalType": signal_type,
            },
        },
        "roulette.sensor_stuck": {
            "msgId": ErrorMsgId.ROULETTE_SENSOR_STUCK.value,
            "content": "Sensor broken causes roulette machine idle",
            "metadata": {
                "title": "SENSOR STUCK",
                "description": "Sensor broken causes roulette machine idle",
                "code": "ARE.3",
                "suggestion": "Clean or replace the ball",
                "signalType": signal_type,
            },
        },
        # Add more mappings as needed
    }
    
    # Default mapping if not found
    default_mapping = {
        "msgId": ErrorMsgId.ROULETTE_INVALID_AFTER_RELAUNCH.value,
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


def broadcast_post_v2_prd(
    url, token, broadcast_type, audience="players", afterSeconds=20
):  # , metadata=None):
    """
    Send a broadcast message to the table

    Args:
        url (str): API endpoint URL
        token (str): Authentication token
        broadcast_type (str): Type of broadcast message (e.g., "roulette.relaunch")
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
    broadcast_data = _get_broadcast_metadata_prd(broadcast_type, signal_type="warning")
    
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
    import random

    cnt = 0
    while cnt < 1:
        results = "0"  # str(random.randint(0, 36))
        # URLs and tokens are now loaded from config file at module level

        # broadcast_post(post_url, token, "roulette.relaunch", "players", 20)
        print("================Start================\n")
        round_id, betPeriod = start_post_v2_prd(post_url, token)
        round_id, status, betPeriod = get_roundID_v2_prd(get_url, token)
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
        time.sleep(13)
        bet_stop_post_prd(post_url, token)
        deal_post_v2_prd(post_url, token, round_id, results)
        print("================Finish================\n")
        finish_post_v2_prd(post_url, token)

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
