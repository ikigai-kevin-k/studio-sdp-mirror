import requests
import json
from pprint import pprint

def print_response(description, response):
    print(f"\n=== {description} ===")
    try:
        # use json.dumps to format the response, ensure chinese characters are displayed correctly
        formatted_json = json.dumps(response.json(), indent=2, ensure_ascii=False)
        print(formatted_json)
    except Exception as e:
        print(f"Error formatting response: {e}")
        print(response.text)
    print("=" * 50)

# get game table info
response = requests.get('http://localhost:8000/v1/service/table/SDP_001')
print_response("get game table info", response)

# login
response = requests.post(
    'http://localhost:8000/v1/service/sdp/table/SDP_001/login',
    headers={'x-sdp-token': 'your-token'}
)
print_response("login response", response)

# start game
response = requests.post(
    'http://localhost:8000/v1/service/sdp/table/SDP_001/start',
    headers={'Bearer': 'Bearer your-token'}
)
print_response("start game response", response)
