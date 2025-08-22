import requests
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import JsonLexer
import json
import time
import sys
import os

# Add the parent directory to path to import slack package
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

try:
    from slack import send_error_to_slack
    SLACK_AVAILABLE = True
    print("✅ Slack notifications enabled")
except ImportError as e:
    print(f"⚠️ Warning: Slack import failed: {e}")
    print("   Slack notifications will be disabled")
    SLACK_AVAILABLE = False


# CIT BCR-001
# Remove hardcoded accessToken and create a function to get fresh token
def get_access_token():
    """Get a fresh access token from the API"""
    url = "https://crystal-table.iki-cit.cc/v2/service/sessions"
    headers = {
        "accept": "application/json",
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
    }
    data = {"gameCode": "BCR-001", "role": "sdp"}

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


def load_config(config_file="conf/table-config-baccarat-v2.json"):
    """
    Load configuration from JSON file
    
    Args:
        config_file (str): Path to configuration file
        
    Returns:
        dict: Configuration for BCR-001 table
    """
    try:
        config_path = os.path.join(project_root, config_file)
        with open(config_path, 'r') as f:
            configs = json.load(f)
        
        # Find BCR-001 configuration
        for config in configs:
            if config.get("game_code") == "BCR-001":
                return config
        
        raise ValueError("BCR-001 configuration not found in config file")
        
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_file}")
        return None
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in config file: {config_file}")
        return None
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None

# Load configuration
config = load_config()
if not config:
    print("Failed to load configuration. Exiting.")
    exit(1)

# Extract configuration values
accessToken = config.get("access_token")
table_token = config.get("table_token")
get_url = config.get("get_url")
post_url = config.get("post_url")
game_code = config.get("game_code")

if not all([accessToken, table_token, get_url, post_url, game_code]):
    print("❌ Missing required configuration values")
    print(f"   access_token: {'✅' if accessToken else '❌'}")
    print(f"   table_token: {'✅' if table_token else '❌'}")
    print(f"   get_url: {'✅' if get_url else '❌'}")
    print(f"   post_url: {'✅' if post_url else '❌'}")
    print(f"   game_code: {'✅' if game_code else '❌'}")
    exit(1)

print(f"✅ Configuration loaded successfully:")
print(f"   Environment: {config.get('name')}")
print(f"   Game Code: {game_code}")
print(f"   Access Token: {accessToken[:50]}...")
print(f"   Table Token: {table_token}")
print(f"   Get URL: {get_url}")
print(f"   Post URL: {post_url}")


def start_post_v2(url, token):
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
        
        # Handle 403 errors
        if response.status_code == 403:
            try:
                error_data = response.json()
                error_code = error_data.get("error", {}).get("code")
                error_message = error_data.get("error", {}).get("message", "")
                
                # Case 1: Round isn't finished yet (code 13003)
                if (error_code == 13003 and 
                    "isn't finished yet" in error_message):
                    
                    print("=== detected previous round not finished, auto pause and wait ===")
                    
                    # Send Slack notification
                    slack_message = "🚨 BCR-001 previous round not finished!\n\n" \
                                  "Dealer needs to:\n" \
                                  "1. Fill in the previous round result\n" \
                                  "2. Manually finish the previous round\n\n" \
                                  "System has automatically paused and entered waiting state..."
                    
                    if SLACK_AVAILABLE:
                        try:
                            send_error_to_slack(slack_message)
                            print("✅ Slack notification sent")
                        except Exception as e:
                            print(f"❌ Slack notification failed: {e}")
                    else:
                        print("⚠️ Slack notifications disabled - message would be:")
                        print(slack_message)
                    
                    # Auto pause the table
                    try:
                        pause_post_v2(url, token, "auto-pause-waiting-for-previous-round")
                        print("✅ Table has automatically paused")
                    except Exception as e:
                        print(f"❌ Auto pause failed: {e}")
                    
                    # Enter idle state and wait for resume
                    return "IDLE_WAITING", "PAUSED"
                
                # Case 2: Table is already paused (code 13007)
                elif (error_code == 13007 and 
                      "table is currently paused" in error_message):
                    
                    print("=== detected table is already paused, waiting for resume ===")
                    
                    # Send Slack notification
                    slack_message = "⏸️ BCR-001 table is already paused!\n\n" \
                                  "Current pause reason: " + \
                                  error_message.split("due to: ")[-1] + "\n\n" \
                                  "System will wait for table to resume..."
                    
                    if SLACK_AVAILABLE:
                        try:
                            send_error_to_slack(slack_message)
                            print("✅ Slack notification sent")
                        except Exception as e:
                            print(f"❌ Slack notification failed: {e}")
                    else:
                        print("⚠️ Slack notifications disabled - message would be:")
                        print(slack_message)
                    
                    # Enter idle state and wait for resume
                    return "IDLE_WAITING", "ALREADY_PAUSED"
                    
            except json.JSONDecodeError:
                pass  # If response is not JSON, continue with normal error handling
        
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


def deal_post_v2(url, token, round_id, result):
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
        # "roulette": result  # 修改: 使用 "roulette" 而不是 "sicBo"，直接傳入數字的string
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

    json_str = json.dumps(response.json(), indent=2)

    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)


def finish_post_v2(url, token):
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


def visibility_post(url, token, enable):
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


def get_roundID_v2(url, token):
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
    
    # 美化輸出 API response
    try:
        response_data = response.json()
        print("=== BCR API Response ===")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print("=== Raw Response (Not JSON) ===")
        print(response.text)
    
    # Check if the response status code indicates success
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        raise Exception(f"Error: {response.status_code} - {response.text}")
        # return -1, -1, -1

    try:
        # Parse the response JSON
        response_data = response.json()
    except json.JSONDecodeError:
        print("Error: Unable to decode JSON response.")
        raise Exception("Error: Unable to decode JSON response.")
        # return -1, -1, -1

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
        # return -1, -1, -1

    # Format the JSON for pretty printing and apply syntax highlighting
    json_str = json.dumps(response_data, indent=2)
    # colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    # print(colored_json)

    return round_id, status, betPeriod


def wait_for_resume(url, token, max_wait_time=300):
    """
    Wait for the table to resume from pause state
    
    Args:
        url (str): API endpoint URL
        token (str): Authentication token
        max_wait_time (int): Maximum wait time in seconds (default: 5 minutes)
    
    Returns:
        bool: True if resumed, False if timeout
    """
    print("=== Enter waiting state, monitor pause status ===")
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        try:
            # Get current table status
            round_id, status, betPeriod = get_roundID_v2(url, token)
            
            # Check if pause is cleared
            if status != "PAUSED" and status != "bet-txn-stopped":
                print(f"✅ Table has resumed! Status: {status}")
                return True
            
            # Check pause reason
            try:
                response = requests.get(f"{url}", headers={
                    "accept": "application/json",
                    "Bearer": f"Bearer {token}",
                    "x-signature": "los-local-signature",
                    "Content-Type": "application/json",
                    "Cookie": f"accessToken={accessToken}",
                    "Connection": "close",
                }, verify=False)
                
                if response.status_code == 200:
                    response_data = response.json()
                    pause_info = response_data.get("data", {}).get("table", {}).get("pause", {})
                    
                    if not pause_info:  # pause is cleared
                        print("✅ pause status cleared, table resumed")
                        return True
                    else:
                        print(f"⏳ Waiting... pause reason: {pause_info.get('reason', 'unknown')}")
                        
            except Exception as e:
                print(f"⚠️ Error checking pause status: {e}")
            
            # Wait 10 seconds before next check
            time.sleep(10)
            
        except Exception as e:
            print(f"⚠️ Error waiting for resume: {e}")
            time.sleep(10)
    
    print(f"⏰ Timeout ({max_wait_time} seconds), please check table status manually")
    return False


def pause_post_v2(url, token, reason):
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


def sdp_config_post(url, token, config_data):
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


def get_sdp_config(url, token):
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

    results = [1, 2, 3]

    # Build full URLs with game code
    get_url = get_url + game_code
    post_url = post_url + game_code
    token = table_token

    print("================Start================\n")
    round_id, betPeriod = start_post_v2(post_url, token)
        
    # Check if we're in IDLE state
    if round_id == "IDLE_WAITING":
        print("🔄 Enter IDLE state, waiting for table to resume...")
        if wait_for_resume(get_url, token):
            print("🔄 Table has resumed, try start again...")
            round_id, betPeriod = start_post_v2(post_url, token)
            if round_id == "IDLE_WAITING":
                print("❌ Table still cannot start, skip this round")
                exit(1)
            else:
                print("❌ Timeout, skip this round")
                exit(1)
        
    if round_id == -1:
        print("❌ start failed, skip this round")
        exit(1)
        
    print(f"✅ Start successful: round_id={round_id}, betPeriod={betPeriod}")
        
    # Get current status
    _, status, _ = get_roundID_v2(get_url, token)
    print(f"Current status: {status}")

    print("================Deal================\n")
    time.sleep(7)
    deal_post_v2(post_url, token, round_id, results)
    print("================Finish================\n")
    finish_post_v2(post_url, token)
