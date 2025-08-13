import requests
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import JsonLexer
import json
import time

#STG ARO-002
# accessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZXNzaW9uSWQiOiI5YTRjNzM5ZC00OWY0LTQ1ZWQtYmVkNi0wYzZkYmQyNzc2NTAiLCJnYW1lQ29kZSI6W10sInJvbGUiOiJzZHAiLCJjcmVhdGVkQXQiOjE3NTA0MTI0MTI4NzEsImlhdCI6MTc1MDQxMjQxMn0.mXjNdwf5iKHeEpLkOlOxzIpLvTQ5aUaKDFMMq_4VS5Q'
accessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZXNzaW9uSWQiOiIxYmNkNTNkNy1mYTJhLTQzYjAtYTgyNS01YTlhZGZmZGQ3NDIiLCJnYW1lQ29kZSI6WyJBUk8tMDAyIl0sInJvbGUiOiJzZHAiLCJjcmVhdGVkQXQiOjE3NTM3NjA1MDE1ODQsImlhdCI6MTc1Mzc2MDUwMX0.EFNTTHjb4X2zs4nXVbmtrJhVDTK-Hux1LwMl5ZJtCM8'
def start_post_v2_stg(url, token):
    # Set up HTTP headers
    headers = {
        'accept': 'application/json',
        'Bearer': f'Bearer {token}',
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json',
        'Cookie': f'accessToken={accessToken}',
        'Connection': 'close'

        # 'timecode': '26000' # 8 + 15 + 3 = 26
    }

    # Define payload for the POST request
    data = {}
    response = requests.post(f'{url}/start', headers=headers, json=data, verify=False)

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
    round_id = response_data.get('data', {}).get('table', {}).get('tableRound', {}).get('roundId')
    betPeriod = response_data.get('data', {}).get('table', {}).get('betPeriod')

    # Handle cases where roundId is not found
    if not round_id:
        print("Error: roundId not found in response.")
        return -1, -1

    # Format the JSON for pretty printing and apply syntax highlighting
    json_str = json.dumps(response_data, indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

    return round_id ,betPeriod

def deal_post_v2_stg(url, token, round_id, result):
    timecode = str(int(time.time() * 1000)+5000)
    headers = {
        'accept': 'application/json',
        'Bearer': token,
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json',
        'timecode': timecode,
        'Cookie': f'accessToken={accessToken}',
        'Connection': 'close'
    }

    data = {
        "roundId": f'{round_id}',
        "roulette": result  # 修改: 使用 "roulette" 而不是 "sicBo"，直接傳入數字的string
    }

    response = requests.post(f'{url}/deal', headers=headers, json=data, verify=False)

    if response.status_code != 200:
        print("====================")
        print("[DEBUG] deal_post_v2")
        print("====================")
        print(f"Error: {response.status_code} - {response.text}")
        print("====================")

    json_str = json.dumps(response.json(), indent=2)

    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

def finish_post_v2_stg(url, token):
    headers = {
        'accept': 'application/json',
        'Bearer': token,
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json',
        'Cookie': f'accessToken={accessToken}',
        'Connection': 'close'
    }
    data = {}
    response = requests.post(f'{url}/finish', headers=headers, json=data, verify=False)
    json_str = json.dumps(response.json(), indent=2)


    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

def visibility_post_stg(url, token, enable):
    headers = {
        'accept': 'application/json',
        'Bearer': token,
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json',
        'Cookie': f'accessToken={accessToken}',
        'Connection': 'close'
    }
    print("enable: ", enable)

    visibility = "disabled" if enable is False else "visible"
    # print("vis: ", visibility)
    data = {
            "visibility": visibility
            }

    response = requests.post(f'{url}/visibility', headers=headers, json=data, verify=False)
    json_str = json.dumps(response.json(), indent=2)

  
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

def get_roundID_v2_stg(url, token):
    # Set up HTTP headers

    # print("URL:", url)

    headers = {
        'accept': 'application/json',
        'Bearer': f'Bearer {token}',
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json',
        'Cookie': f'accessToken={accessToken}',
        'Connection': 'close'
    }

    # Define payload for the POST request
    data = {}
    response = requests.get(f'{url}', headers=headers, verify=False)

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
    round_id = response_data.get('data', {}).get('table', {}).get('tableRound', {}).get('roundId')
    status = response_data.get('data', {}).get('table', {}).get('tableRound', {}).get('status')
    betPeriod = response_data.get('data', {}).get('table', {}).get('betPeriod')

    
    # Handle cases where roundId is not found
    if not round_id:
        print("Error: roundId not found in response.")
        return -1, -1, -1

    # Format the JSON for pretty printing and apply syntax highlighting
    json_str = json.dumps(response_data, indent=2)
    # colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    # print(colored_json)

    return round_id, status, betPeriod

def pause_post_v2_stg(url, token, reason):
    headers = {
        'accept': 'application/json',
        'Bearer': token,
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json',
        'Cookie': f'accessToken={accessToken}',
        'Connection': 'close'
    }

    data = {
        "reason": reason # for example: "cannot drive the dice shaker"
    }

    response = requests.post(f'{url}/pause', headers=headers, json=data, verify=False)
    json_str = json.dumps(response.json(), indent=2)

    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

def resume_post_v2_stg(url, token):
    headers = {
        'accept': 'application/json',
        'Bearer': token,
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json',
        'Cookie': f'accessToken={accessToken}',
        'Connection': 'close'
    }

    data = {}  # Empty payload as per API specification
    response = requests.post(f'{url}/resume', headers=headers, json=data, verify=False)
    json_str = json.dumps(response.json(), indent=2)

    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

def sdp_config_post_v2_stg(url, token, config_data):
    """
    Update SDP configuration for a specific table
    
    Args:
        url (str): API endpoint URL
        token (str): Authentication token
        config_data (dict): Configuration data containing strings and number
    """
    # Modify the URL to use the correct endpoint
    # Remove 'sdp/' from the URL path
    base_url = url.replace('/sdp/table/', '/table/')
    
    headers = {
        'accept': 'application/json',
        'Bearer': token,
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json',
        'Cookie': f'accessToken={accessToken}',
        'Connection': 'close'
    }

    response = requests.post(f'{base_url}/sdp-config', headers=headers, json=config_data, verify=False)
    
    # Format and display the response
    json_str = json.dumps(response.json(), indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

def get_sdp_config_v2_stg(url, token):
    """
    Get SDP configuration from the table status
    
    Args:
        url (str): API endpoint URL
        token (str): Authentication token
    
    Returns:
        tuple: (strings, number) from sdpConfig, or (None, None) if not found
    """
    headers = {
        'accept': 'application/json',
        'Bearer': f'Bearer {token}',
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json',
        'Cookie': f'accessToken={accessToken}',
        'Connection': 'close'
    }

    response = requests.get(f'{url}', headers=headers, verify=False)

    if response.status_code != 200:
        return None, None

    try:
        response_data = response.json()
        sdp_config = response_data.get('data', {}).get('table', {}).get('sdpConfig', {})
        
        broker_host = sdp_config.get('broker_host')
        broker_port = sdp_config.get('broker_port')
        room_id = sdp_config.get('room_id')
        
        return broker_host, broker_port, room_id

    except json.JSONDecodeError:
        print("Error: Unable to decode JSON response.")
        return None, None

def update_sdp_config_from_file_v2_stg(url, token, config_file='sdp.config'):
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
        with open(config_file, 'r') as f:
            config = json.load(f)
            
        # Convert the config values to string format for SDP config
        config_data = {
            "strings": json.dumps({
                "shake_duration": config.get('shake_duration', 8),
                "result_duration": config.get('result_duration', 12)
            }),
            "number": 0  # Default value as it's not used for durations
        }
        
        sdp_config_post_v2_stg(url, token, config_data)
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

def cancel_post_v2_stg(url: str, token: str) -> None:
    """
    取消當前局次
    """
    try:
        headers = {
            'accept': 'application/json',
            'Bearer': token,
            'x-signature': 'los-local-signature',
            'Content-Type': 'application/json',
            'Cookie': f'accessToken={accessToken}',
            'Connection': 'close'
        }
        data = {}
        response = requests.post(f"{url}/cancel", headers=headers, json=data, verify=False)
        response_data = response.json() if response.text else None
        
        # 改進錯誤處理
        if response.status_code != 200:
            error_msg = response_data.get('error', {}).get('message', 'Unknown error') if response_data else f'HTTP {response.status_code}'
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

def broadcast_post_v2_stg(url, token, broadcast_type, audience="players", afterSeconds=20): #, metadata=None):
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
        'accept': 'application/json',
        'Bearer': token,
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json',
        'Cookie': f'accessToken={accessToken}'
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
            "afterSeconds": afterSeconds
        }#metadata or {}
    }

    response = requests.post(f'{url}/broadcast', headers=headers, json=data, verify=False)
    json_str = json.dumps(response.json(), indent=2)

    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

if __name__ == "__main__":
    import random
    cnt = 0
    while cnt < 1:
        results = "0" #str(random.randint(0, 36))
        get_url = 'https://crystal-table.iki-stg.cc/v2/service/tables/'
        post_url = 'https://crystal-table.iki-stg.cc/v2/service/tables/'
        gameCode = 'ARO-002'
        get_url = get_url + gameCode
        post_url = post_url + gameCode
        token = 'E5LN4END9Q'

        # broadcast_post(post_url, token, "roulette.relaunch", "players", 20)
        # print("================Start================\n")
        # round_id, betPeriod = start_post_v2_stg(post_url, token)
        round_id, status, betPeriod =  get_roundID_v2_stg(get_url, token)
        print(round_id, status, betPeriod) 

        # betPeriod = 10
        # print(round_id, status, betPeriod) 
        # while betPeriod >= 0: #or status !='bet-stopped':
        #     print("Bet Period count down:", betPeriod)
        #     time.sleep(1)
        #     betPeriod = betPeriod - 1
        #     _, status, _ =  get_roundID_v2_stg(get_url, token)
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
        # time.sleep(18)
        deal_post_v2_stg(post_url, token, round_id, results)
        print("================Finish================\n")
        finish_post_v2_stg(post_url, token)

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

        cnt+=1