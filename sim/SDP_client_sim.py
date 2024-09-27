import requests
import time
import serial
import threading

class SDPClient:
    def __init__(self, base_url='http://localhost:5000', serial_port=None):
        self.base_url = base_url
        self.serial_port = serial_port
        self.serial = None
        if serial_port:
            self.serial = serial.Serial(serial_port, 9600, timeout=1)

    def get_game_parameters(self):
        try:
            response = requests.get(f'{self.base_url}/get_game_parameters')
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Get game parameters error: {e}")
            return None

    def read_serial_data(self):
        while True:
            if self.serial and self.serial.in_waiting > 0:
                data = self.serial.readline().decode().strip()
                print(f"Received from roulette: {data}")

    def start_polling(self, interval=5):
        if self.serial:
            serial_thread = threading.Thread(target=self.read_serial_data)
            serial_thread.daemon = True
            serial_thread.start()

        while True:
            game_params = self.get_game_parameters()
            if game_params:
                print("Game status:", game_params.get('game_status'))
                print("Game mode:", game_params.get('game_mode'))
                print("Last updated:", game_params.get('last_updated'))
                print("---")
            time.sleep(interval)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        serial_port = sys.argv[1]
    else:
        serial_port = input("Enter the virtual serial port name (e.g., /dev/ttys001): ")
    
    client = SDPClient(serial_port=serial_port)
    try:
        client.start_polling()
    except KeyboardInterrupt:
        print("Stopping client...")
    finally:
        if client.serial:
            client.serial.close()