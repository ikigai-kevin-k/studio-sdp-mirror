import requests
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import JsonLexer
import json
import time
from typing import Tuple
import logging


def start_post(url: str, token: str) -> Tuple[str, int]:
    """
    Send start post request to LOS
    Returns: (round_id, bet_period)
    """
    headers = {
        'accept': 'application/json',
        'Bearer': f'Bearer {token}',
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json'
    }

    data = {}  # 空的 JSON payload
    response = requests.post(f'{url}/start', headers=headers, json=data)

    if response.status_code != 200:
        logging.error(f"Failed to get round ID. Status: {response.status_code}, Response: {response.text}")
        return "-1", 0

    try:
        response_data = response.json()
        round_id = response_data.get('data', {}).get('table', {}).get('tableRound', {}).get('roundId')
        bet_period = response_data.get('data', {}).get('table', {}).get('betPeriod', 30)
        
        if not round_id:
            logging.error("Round ID not found in response")
            return "-1", 0
            
        return round_id, bet_period
        
    except Exception as e:
        logging.error(f"Error in start_post: {str(e)}")
        return "-1", 0

def deal_post(url: str, token: str, round_id: str, result: str) -> bool:
    """Send deal post request to LOS"""
    headers = {
        'accept': 'application/json',
        'Bearer': f'Bearer {token}',
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json'
    }

    # 修正結果格式為 sicBo
    data = {
        "roundId": round_id,
        "sicBo": result  # 使用正確的 key 名稱
    }

    try:
        response = requests.post(f'{url}/deal', headers=headers, json=data)
        json_str = json.dumps(response.json(), indent=2)
        colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
        print(colored_json)
        return response.status_code == 200
    except Exception as e:
        logging.error(f"Error in deal_post: {str(e)}")
        return False

def finish_post(url: str, token: str) -> bool:
    """Send finish post request to LOS"""
    headers = {
        'accept': 'application/json',
        'Bearer': f'Bearer {token}',
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json'
    }

    data = {}  # 空的 JSON payload
    response = requests.post(f'{url}/finish', headers=headers, json=data)
    json_str = json.dumps(response.json(), indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)
    return response.status_code == 200

def visibility_post(url, token, enable):
    headers = {
        'accept': 'application/json',
        'Bearer': token,
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json'
    }
    print("enable: ", enable)

    visibility = "disabled" if enable is False else "visible"
    # print("vis: ", visibility)
    data = {
            "visibility": visibility
            }

    response = requests.post(f'{url}/visibility', headers=headers, json=data)
    json_str = json.dumps(response.json(), indent=2)

  
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

def get_roundID(url, token):
    # Set up HTTP headers

    # print("URL:", url)

    headers = {
        'accept': 'application/json',
        'Bearer': f'Bearer {token}',
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json'
    }

    # Define payload for the POST request
    data = {}
    response = requests.get(f'{url}', headers=headers)

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

def pause_post(url, token, reason):
    headers = {
        'accept': 'application/json',
        'Bearer': token,
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json'
    }

    data = {
        "reason": reason # for example: "cannot drive the dice shaker"
    }

    response = requests.post(f'{url}/pause', headers=headers, json=data)
    json_str = json.dumps(response.json(), indent=2)

    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

def resume_post(url, token):
    headers = {
        'accept': 'application/json',
        'Bearer': token,
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json'
    }

    data = {}  # Empty payload as per API specification
    response = requests.post(f'{url}/resume', headers=headers, json=data)
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
    base_url = url.replace('/sdp/table/', '/table/')
    
    headers = {
        'accept': 'application/json',
        'Bearer': token,
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json'
    }

    response = requests.post(f'{base_url}/sdp-config', headers=headers, json=config_data)
    
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
        'accept': 'application/json',
        'Bearer': f'Bearer {token}',
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json'
    }

    response = requests.get(f'{url}', headers=headers)

    if response.status_code != 200:
        return None, None

    try:
        response_data = response.json()
        sdp_config = response_data.get('data', {}).get('table', {}).get('sdpConfig', {})
        
        strings = sdp_config.get('strings')
        number = sdp_config.get('number')
        
        return strings, number

    except json.JSONDecodeError:
        print("Error: Unable to decode JSON response.")
        return None, None

def update_sdp_config_from_file(url, token, config_file='sdp.config'):
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

def cancel_post(url, token):
    """
    Send a POST request to cancel the current round
    
    Args:
        url (str): API endpoint URL
        token (str): Authentication token
    """
    # Modify the URL to use the correct endpoint
    # Replace 'sdp/table' with 'fm/table' in the URL path
    fm_url = url.replace('/sdp/table/', '/fm/table/')
    
    headers = {
        'accept': 'application/json',
        'Bearer': token,
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json'
    }

    data = {}  # Empty payload as per API specification
    response = requests.post(f'{fm_url}/cancel', headers=headers, json=data)
    json_str = json.dumps(response.json(), indent=2)

    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

def create_los_urls(base_url: str, game_code: str) -> Tuple[str, str]:
    """Create LOS API URLs"""
    get_url = f"{base_url}/v1/service/table/{game_code}"
    post_url = f"{base_url}/v1/service/sdp/table/{game_code}"
    return get_url, post_url

def check_los_state(url: str, token: str) -> Tuple[int, str, str]:
    """Check LOS system state"""
    try:
        return get_roundID(url, token)
    except Exception as e:
        raise Exception(f"Failed to get LOS state: {e}")

if __name__ == "__main__":

    results = [1, 2, 3]
    get_url = 'https://crystal-los.iki-cit.cc/v1/service/table/'
    post_url = 'https://crystal-los.iki-cit.cc/v1/service/sdp/table/'
    gameCode = 'SDP-003'
    get_url = get_url + gameCode
    post_url = post_url + gameCode
    token = 'E5LN4END9Q'

    # round_id, betPeriod = start_post(post_url, token)
    # print("================Start================\n")
    
    round_id, status, betPeriod =  get_roundID(get_url, token)
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
    # time.sleep(12)


    # print("================Deal================\n")
    time.sleep(15)
    deal_post(post_url, token, round_id, results)
    # print("================Finish================\n")
    finish_post(post_url, token)

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