import requests
import time

"""
This is the manager simulator. It simulates the manager sending requests to the LOS.
"""

class ManagerSimulator:
    def manager_send_request(self, manual_end_game):
        """
        Todo:
        - Add more manager request types
        - Rename manual_end_game to power_off_roulette, but need to rename the parameter in the LOS first, then rename SDP
        """
        LOS_url = 'http://127.0.0.1:5000/set_game_parameter'
        headers = {'Content-Type': 'application/json'}
        manager_request_data = {'manual_end_game': manual_end_game}
        
        try:
            response = requests.post(LOS_url, json=manager_request_data, headers=headers)
            if response.status_code == 200:
                print(f"Successfully set manual_end_game to {manual_end_game}")
            else:
                print(f"Failed to set manual_end_game. Status code: {response.status_code}")
        except requests.RequestException as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":

    print("Manager simulator started. Press Ctrl+C to stop.")
    manager = ManagerSimulator()
    try:
        while True:
            manager.manager_send_request(True)
            time.sleep(2)
            manager.manager_send_request(False)
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nManager simulator stopped.")
