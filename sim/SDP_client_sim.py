import requests
import time
import serial
import threading


"""
SDP should be able to automatically deal with the command from/to LOS and roulette.
"""

class StateMachine:
    """
    Refer to Cammegh SS2 Owner's handbook, p.49,
    First, implement the naive state transition logic without any external interruptions and internal errors.

    """


    def __init__(self):
        self.data_protocol_modes = ["game_mode","operation_mode","self_test_mode", "power_setting_mode","calibration_mode", "warning_flag_mode", "statistics_mode"]
        self.power_states = ["on", "off"]
        self.game_states = ["idle","start_game","place_bet","ball_launch","no_more_bet","winning_number","table_closed"]
        self.current_game_state = "idle"

    def transition(self, new_game_state):
        self.current_game_state = new_game_state

    def naive_state_machine(self):
        """
        Transition logic (without perturbations):
        1->2->3->4->5->1... until 6 interrupts
        """
        match self.current_game_state:
            case "start_game":
                self.transition("place_bet")
            case "place_bet":
                self.transition("ball_launch")
            case "ball_launch":
                self.transition("no_more_bet")
            case "no_more_bet":
                self.transition("winning_number")
            case "winning_number":
                self.transition("start_game")
            case "table_closed":
                self.transition("idle")

class SDPClient:
    def __init__(self, LOS_server_url='http://localhost:5000', roulette_serial_port_number=None): 
        """
        LOS_server_url: the url of the LOS server
        roulette_serial_port_number: the port number of the virtual serial port of Roulette machine simulator
        """
        self.LOS_server_url = LOS_server_url
        self.roulette_serial_port_number = roulette_serial_port_number
        self.SDP_serial_port = None
        if roulette_serial_port_number:
            self.SDP_serial_port = serial.Serial(roulette_serial_port_number, 9600, timeout=1)

    def sdp_get_game_parameters(self):
        try:
            response = requests.get(f'{self.LOS_server_url}/get_game_parameters')
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Get game parameters error: {e}")
            return None

    def sdp_send_to_roulette(self, manual_end_game, use_command_file=True):
        """
        To be refactored: rename c to P (stands for power on/off)
        """
        if self.SDP_serial_port: 

            if not use_command_file:
                # Assuming we use the 'c' field in the protocol to represent manual_end_game
                x, y, z, a, b = 1, 0, 24, 0, 0  # Default values
                c = 1 if manual_end_game else 0
                roulette_protocol_data = f"*X:{x:01d}:{y:03d}:{z:02d}:{a:01d}:{b:03d}:{c:01d}\r\n"
                self.SDP_serial_port.write(roulette_protocol_data.encode())
                print(f"Sent to roulette: {roulette_protocol_data.strip()}")

            else:
                """
                To be implemented: SDP send the commands in the command file sequentially to the roulette
                """
                pass

    def sdp_read_serial_data(self):
        while True:
            if self.SDP_serial_port and self.SDP_serial_port.in_waiting > 0:
                roulette_protocol_data = self.SDP_serial_port.readline().decode().strip()
                print(f"Received from roulette: {roulette_protocol_data}")

    def sdp_start_polling(self, interval=0.5): # ask Cammegh support staff about the interval
        if self.SDP_serial_port:
            serial_thread = threading.Thread(target=self.sdp_read_serial_data)
            serial_thread.daemon = True
            serial_thread.start()

        last_manual_end_game = None

        while True:
            game_params = self.sdp_get_game_parameters()
            if game_params:
                # To be updated: rename all manual_end_game to power_off_game
                print("Game status:", game_params.get('game_status'))
                print("Game mode:", game_params.get('game_mode'))
                print("Last updated:", game_params.get('last_updated'))
                manual_end_game = game_params.get('game_parameters', {}).get('manual_end_game')
                print("Manual end game:", manual_end_game)

                if manual_end_game != last_manual_end_game:
                    self.sdp_send_to_roulette(manual_end_game)
                    last_manual_end_game = manual_end_game
                
                print("--------------------------------")

            time.sleep(interval)

if __name__ == '__main__':

    import sys
    
    if len(sys.argv) > 1:
        roulette_serial_port_number = sys.argv[1]
    else:
        roulette_serial_port_number = input("Enter the virtual serial port number (e.g., /dev/ttys001): ")
    
    client = SDPClient(roulette_serial_port_number=roulette_serial_port_number)

    try:
        client.sdp_start_polling()
    except KeyboardInterrupt:
        print("Stop client...")
    finally:
        if client.SDP_serial_port:
            print("Close SDP serial port...")
            client.SDP_serial_port.close()
