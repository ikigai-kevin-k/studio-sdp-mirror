import requests
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import JsonLexer
import json
import time
import os

# Load configuration from JSON file
def load_config(env_name):
    """
    Load configuration from table-config-speed-roulette-v2.json
    
    Args:
        env_name (str): Environment name (PRD, UAT, CIT, STG, QAT)
    
    Returns:
        dict: Configuration dictionary for the specified environment
    """
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "conf", "table-config-speed-roulette-v2.json")
    try:
        with open(config_path, "r") as f:
            configs = json.load(f)
            # Find specified environment configuration
            for config in configs:
                if config["name"] == env_name:
                    return config
        raise Exception(f"{env_name} configuration not found in config file")
    except Exception as e:
        print(f"Error loading config for {env_name}: {e}")
        return None

# Initialize configuration for specified environment
def init_config(env_name):
    """
    Initialize configuration variables for the specified environment
    
    Args:
        env_name (str): Environment name (PRD, UAT, CIT, STG, QAT)
    
    Returns:
        tuple: (accessToken, gameCode, get_url, post_url, token) or None if failed
    """
    config = load_config(env_name)
    if config:
        accessToken = config["access_token"]
        gameCode = config["game_code"]
        get_url = config["get_url"] + gameCode
        post_url = config["post_url"] + gameCode
        token = config["table_token"]
        return accessToken, gameCode, get_url, post_url, token
    else:
        print(f"Failed to load configuration for {env_name}")
        return None

def start_post(url, token, accessToken):
    """
    Start a new round
    
    Args:
        url (str): API endpoint URL
        token (str): Table token
        accessToken (str): Access token
    
    Returns:
        tuple: (round_id, betPeriod) or (-1, -1) if failed
    """
    headers = {
        "accept": "application/json",
        "Bearer": f"Bearer {token}",
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={accessToken}",
        "Connection": "close",
    }

    data = {}
    response = requests.post(
        f"{url}/start", headers=headers, json=data, verify=False
    )

    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return -1, -1

    try:
        response_data = response.json()
    except json.JSONDecodeError:
        print("Error: Unable to decode JSON response.")
        return -1, -1

    round_id = (
        response_data.get("data", {})
        .get("table", {})
        .get("tableRound", {})
        .get("roundId")
    )
    betPeriod = response_data.get("data", {}).get("table", {}).get("betPeriod")

    if not round_id:
        print("Error: roundId not found in response.")
        return -1, -1

    # Format and display the response
    json_str = json.dumps(response_data, indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

    return round_id, betPeriod

def deal_post(url, token, accessToken, round_id, result):
    """
    Send deal result
    
    Args:
        url (str): API endpoint URL
        token (str): Table token
        accessToken (str): Access token
        round_id (str): Round ID
        result (str): Deal result
    """
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
        "roulette": result,
    }

    response = requests.post(
        f"{url}/deal", headers=headers, json=data, verify=False
    )

    if response.status_code != 200:
        print("====================")
        print("[DEBUG] deal_post")
        print("====================")
        print(f"Error: {response.status_code} - {response.text}")
        print("====================")

    json_str = json.dumps(response.json(), indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

def finish_post(url, token, accessToken):
    """
    Finish the current round
    
    Args:
        url (str): API endpoint URL
        token (str): Table token
        accessToken (str): Access token
    """
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

def visibility_post(url, token, accessToken, enable):
    """
    Set table visibility
    
    Args:
        url (str): API endpoint URL
        token (str): Table token
        accessToken (str): Access token
        enable (bool): True for visible, False for disabled
    """
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

def get_roundID(url, token, accessToken):
    """
    Get current round information
    
    Args:
        url (str): API endpoint URL
        token (str): Table token
        accessToken (str): Access token
    
    Returns:
        tuple: (round_id, status, betPeriod) or (-1, -1, -1) if failed
    """
    headers = {
        "accept": "application/json",
        "Bearer": f"Bearer {token}",
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={accessToken}",
        "Connection": "close",
    }

    data = {}
    response = requests.get(f"{url}", headers=headers, verify=False)

    if response.status_code != 200:
        return -1, -1, -1

    try:
        response_data = response.json()
    except json.JSONDecodeError:
        print("Error: Unable to decode JSON response.")
        return -1, -1, -1

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

    if not round_id:
        print("Error: roundId not found in response.")
        return -1, -1, -1

    return round_id, status, betPeriod

def pause_post(url, token, accessToken, reason):
    """
    Pause the current round
    
    Args:
        url (str): API endpoint URL
        token (str): Table token
        accessToken (str): Access token
        reason (str): Reason for pausing
    """
    headers = {
        "accept": "application/json",
        "Bearer": token,
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={accessToken}",
        "Connection": "close",
    }

    data = {"reason": reason}

    response = requests.post(
        f"{url}/pause", headers=headers, json=data, verify=False
    )
    json_str = json.dumps(response.json(), indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

def resume_post(url, token, accessToken):
    """
    Resume the current round
    
    Args:
        url (str): API endpoint URL
        token (str): Table token
        accessToken (str): Access token
    """
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
        f"{url}/resume", headers=headers, json=data, verify=False
    )
    json_str = json.dumps(response.json(), indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

def sdp_config_post(url, token, accessToken, config_data):
    """
    Update SDP configuration for a specific table
    
    Args:
        url (str): API endpoint URL
        token (str): Table token
        accessToken (str): Access token
        config_data (dict): Configuration data containing strings and number
    """
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

    json_str = json.dumps(response.json(), indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

def get_sdp_config(url, token, accessToken):
    """
    Get SDP configuration from the table status
    
    Args:
        url (str): API endpoint URL
        token (str): Table token
        accessToken (str): Access token
    
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

def update_sdp_config_from_file(url, token, accessToken, config_file="sdp.config"):
    """
    Read configuration from sdp.config file and update SDP configuration
    
    Args:
        url (str): API endpoint URL
        token (str): Table token
        accessToken (str): Access token
        config_file (str): Path to the config file
    
    Returns:
        bool: True if update successful, False otherwise
    """
    try:
        with open(config_file, "r") as f:
            config = json.load(f)

        config_data = {
            "strings": json.dumps(
                {
                    "shake_duration": config.get("shake_duration", 8),
                    "result_duration": config.get("result_duration", 12),
                }
            ),
            "number": 0,
        }

        sdp_config_post(url, token, accessToken, config_data)
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

def cancel_post(url, token, accessToken):
    """
    Cancel the current round
    
    Args:
        url (str): API endpoint URL
        token (str): Table token
        accessToken (str): Access token
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

        if response.status_code != 200:
            if response_data:
                error_msg = response_data.get("error", {}).get("message", "Unknown error")
            else:
                error_msg = f"HTTP {response.status_code}"
            print(f"Error in cancel_post: {error_msg}")
            return

        if response_data is None:
            print("Warning: Empty response from server")
            return

        if response_data and "error" in response_data and response_data["error"]:
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

def broadcast_post(url, token, accessToken, broadcast_type, audience="players", afterSeconds=20):
    """
    Send a broadcast message to the table
    
    Args:
        url (str): API endpoint URL
        token (str): Table token
        accessToken (str): Access token
        broadcast_type (str): Type of broadcast message (e.g., "dice.reroll")
        audience (str): Target audience for the broadcast (default: "players")
        afterSeconds (int): Delay in seconds before broadcast (default: 20)
    """
    headers = {
        "accept": "application/json",
        "Bearer": token,
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={accessToken}",
        "Connection": "close",
    }

    msg_id = f"msg_{int(time.time() * 1000)}"

    data = {
        "msgId": msg_id,
        "metadata": {
            "type": broadcast_type,
            "audience": audience,
            "afterSeconds": afterSeconds,
        },
    }

    response = requests.post(
        f"{url}/broadcast", headers=headers, json=data, verify=False
    )
    json_str = json.dumps(response.json(), indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

# Convenience function to run a complete game cycle
def run_game_cycle(env_name, result="0"):
    """
    Run a complete game cycle for the specified environment
    
    Args:
        env_name (str): Environment name (PRD, UAT, CIT, STG, QAT)
        result (str): Deal result (default: "0")
    """
    print(f"================Running Game Cycle for {env_name}================\n")
    
    # Initialize configuration
    config_result = init_config(env_name)
    if not config_result:
        print(f"Failed to initialize configuration for {env_name}")
        return
    
    accessToken, gameCode, get_url, post_url, token = config_result
    
    try:
        # Get current round info
        print("================Get Round Info================\n")
        round_id, status, betPeriod = get_roundID(get_url, token, accessToken)
        if round_id == -1:
            print("Failed to get round information")
            return
        print(f"Round ID: {round_id}, Status: {status}, Bet Period: {betPeriod}")
        
        # Deal result
        print("================Deal================\n")
        deal_post(post_url, token, accessToken, round_id, result)
        
        # Finish round
        print("================Finish================\n")
        finish_post(post_url, token, accessToken)
        
        print(f"================Game Cycle Completed for {env_name}================\n")
        
    except Exception as e:
        print(f"Error during game cycle: {e}")

if __name__ == "__main__":
    import random
    
    # Example usage - you can change the environment here
    ENV = "CIT"  # Change to PRD, UAT, STG, QAT as needed
    result = "0"  # str(random.randint(0, 36))
    
    # Run complete game cycle
    run_game_cycle(ENV, result)
    
    # Or use individual functions
    # config_result = init_config(ENV)
    # if config_result:
    #     accessToken, gameCode, get_url, post_url, token = config_result
    #     
    #     # Example: Get round info
    #     round_id, status, betPeriod = get_roundID(get_url, token, accessToken)
    #     print(f"Round ID: {round_id}, Status: {status}, Bet Period: {betPeriod}")
    #     
    #     # Example: Set visibility
    #     visibility_post(post_url, token, accessToken, True)
