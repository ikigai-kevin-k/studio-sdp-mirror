import requests
import time
import sys

def send_request(manual_end_game):
    url = 'http://127.0.0.1:5000/set_game_parameter'
    headers = {'Content-Type': 'application/json'}
    data = {'manual_end_game': manual_end_game}
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            print(f"Successfully set manual_end_game to {manual_end_game}")
        else:
            print(f"Failed to set manual_end_game. Status code: {response.status_code}")
    except requests.RequestException as e:
        print(f"Request failed: {e}")

def main():
    print("Manager simulator started. Press Ctrl+C to stop.")
    try:
        while True:
            send_request(True)
            time.sleep(2)
            send_request(False)
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nManager simulator stopped.")

if __name__ == "__main__":
    main()
