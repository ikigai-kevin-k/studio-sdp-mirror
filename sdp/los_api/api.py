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
        print(f"Error: {response.status_code} - {response.text}")
        return -1

    try:
        # Parse the response JSON
        response_data = response.json()
    except json.JSONDecodeError:
        print("Error: Unable to decode JSON response.")
        return -1

    # Extract roundId from the nested JSON structure
    round_id = response_data.get('data', {}).get('table', {}).get('tableRound', {}).get('roundId')

    # Handle cases where roundId is not found
    if not round_id:
        print("Error: roundId not found in response.")
        return -1

    # Format the JSON for pretty printing and apply syntax highlighting
    json_str = json.dumps(response_data, indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

    return round_id

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

def get_roundID(gameCode, token):
    # Set up HTTP headers

    src_url = 'https://crystal-los.iki-cit.cc/v1/service/table/'
    gameCode = 'SDP-001'
    url = src_url + gameCode
    print("UUUUUUUUUUUU:", url)

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
        print(f"Error: {response.status_code} - {response.text}")
        return -1

    try:
        # Parse the response JSON
        response_data = response.json()
    except json.JSONDecodeError:
        print("Error: Unable to decode JSON response.")
        return -1

    # Extract roundId from the nested JSON structure
    round_id = response_data.get('data', {}).get('table', {}).get('tableRound', {}).get('roundId')

    # Handle cases where roundId is not found
    if not round_id:
        print("Error: roundId not found in response.")
        return -1

    # Format the JSON for pretty printing and apply syntax highlighting
    json_str = json.dumps(response_data, indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

    return round_id




if __name__ == "__main__":

    results = [1, 2, 3]
    round_id = 'SDP-001-20250210-053030'
    src_url = 'https://crystal-los.iki-cit.cc/v1/service/sdp/table/'
    gameCode = 'SDP-001'
    url = src_url + gameCode
    token = 'E5LN4END9Q'

    # start_post(url, token)

    print("================Get================\n")
    round_id = get_roundID(gameCode, token)

    # time.sleep(5)
    print("================Deal================\n")
    deal_post(url, token, round_id, results)
    print("================Finish================\n")
    finish_post(url, token)