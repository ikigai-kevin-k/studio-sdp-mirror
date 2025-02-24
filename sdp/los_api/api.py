import requests
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import JsonLexer
import json
import time


def start_post(url, token):
    # Set up HTTP headers
    headers = {
        'accept': 'application/json',
        'Bearer': f'Bearer {token}',
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json'
    }

    # Define payload for the POST request
    data = {}
    response = requests.post(f'{url}/start', headers=headers, json=data)

    # Check if the response status code indicates success
    if response.status_code != 200:
        # print(f"Error: {response.status_code} - {response.text}")
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

def deal_post(url, token, round_id, result):
    headers = {
        'accept': 'application/json',
        'Bearer': token,
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json'
    }

    data = {
        "roundId": f'{round_id}', # replaced with the roundId receive from start request
        "sicBo": result # for test, to be replaced with the actual values read from log file
    }

    response = requests.post(f'{url}/deal', headers=headers, json=data)
    json_str = json.dumps(response.json(), indent=2)


    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

def finish_post(url, token):
    headers = {
        'accept': 'application/json',
        'Bearer': token,
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json'
    }

    data = {}
    response = requests.post(f'{url}/finish', headers=headers, json=data)
    json_str = json.dumps(response.json(), indent=2)


    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

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

if __name__ == "__main__":

    results = [1, 2, 3]
    get_url = 'https://crystal-los.iki-cit.cc/v1/service/table/'
    post_url = 'https://crystal-los.iki-cit.cc/v1/service/sdp/table/'
    gameCode = 'SDP-003'
    get_url = get_url + gameCode
    post_url = post_url + gameCode
    token = 'E5LN4END9Q'

    # round_id, betPeriod = start_post(post_url, token)
    # # # # print("================Start================\n")
    
    round_id, status, betPeriod =  get_roundID(get_url, token)
    # print(round_id, status, betPeriod) 
    # while betPeriod > 0 or status !='bet-stopped':
    #     print("Bet Period count down:", betPeriod)
    #     time.sleep(1)
    #     betPeriod = betPeriod - 1
    #     _, status, _ =  get_roundID(get_url, token)

    # # print("================Pause================\n")
    # # pause_post(post_url, token, "test")
    # # time.sleep(1)
    
    # # print("================Resume================\n")
    resume_post(post_url, token)  
    # # time.sleep(1)

    # print("================Invisibility================\n")
    # visibility_post(post_url, token, False)
    # time.sleep(1)

    # print("================Visibility================\n")
    # visibility_post(post_url, token, True)
    # time.sleep(12)


    # # print("================Deal================\n")
    # # time.sleep(12)
    deal_post(post_url, token, round_id, results)
    # # print("================Finish================\n")
    finish_post(post_url, token)