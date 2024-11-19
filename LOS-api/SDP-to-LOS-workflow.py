import requests
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import JsonLexer
import json
import random
import time

# common config
BASE_URL = 'https://crystal-rgs.iki-cit.cc/v1/service/sdp/table/SDP-001'
TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZHBUb2tlbiI6IkU1TE40RU5EOVEiLCJnYW1lQ29kZSI6IlNEUC0wMDEiLCJpYXQiOjE3MzIwMDEwMzJ9.jY_f50K1To9wsaFRcd1NM6PT7VXNbjJJcHslfnUdq0M'

headers = {
    'accept': 'application/json',
    'Bearer': f'Bearer {TOKEN}',
    'x-signature': 'live-rgs-local-signature',
    'Content-Type': 'application/json'
}

def print_response(response):
    json_str = json.dumps(response.json(), indent=2)
    colored_json = highlight(json_str, JsonLexer(), TerminalFormatter())
    print(colored_json)

def workflow():
    # 1. Start
    print("\nrunning start...")
    start_response = requests.post(f'{BASE_URL}/start', headers=headers, json={})
    print_response(start_response)
    
    # get roundId and betStopTime
    response_data = start_response.json()
    round_id = response_data['data']['table']['tableRound']['roundId']
    bet_stop_time = response_data['data']['table']['tableRound']['betStopTime']
    print("round_id: ", round_id)
    print("bet_stop_time: ", bet_stop_time)
    
    if not round_id:
        print("error: failed to get roundId")
        return
    
    # waiting until the bet period ends
    print("\nwaiting for bet period to end...")
    bet_stop_timestamp = time.mktime(time.strptime(bet_stop_time.replace('Z', 'GMT'), '%Y-%m-%dT%H:%M:%S.%f%Z'))
    current_timestamp = time.time()
    wait_time = max(0, bet_stop_timestamp - current_timestamp)
    time.sleep(wait_time)
    
    # 2. Deal
    print("\nrunning deal...")
    deal_data = {
        "roundId": round_id,
        "roulette": random.randint(0, 36)
    }
    deal_response = requests.post(f'{BASE_URL}/deal', headers=headers, json=deal_data)
    print_response(deal_response)
    
    # 3. waiting 5 seconds to ensure the result is processed
    print("\nwaiting 5 seconds...")
    time.sleep(5)
    
    # 4. Finish
    print("\nrunning finish...")
    finish_response = requests.post(f'{BASE_URL}/finish', headers=headers, json={})
    print_response(finish_response)

if __name__ == "__main__":
    workflow()