import time
import os
import pty
import threading
import random
from itertools import islice

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
        self.current_data_protocol_mode = None 
        self.current_power_state = "off"

    def game_state_transition_to(self, new_game_state):
        self.current_game_state = new_game_state
        """
        Duration, refer to log and video
        """
        time.sleep(1) 

    def normal_state_machine(self):
        """
        Transition logic (without perturbations):
        1->2->3->4->5->1... until 6 interrupts
        """
        match self.current_game_state:
            case "start_game":
                self.transition("place_bet")
                """
                Duration, refer to log and video
                """
                pass 
            case "place_bet":
                self.transition("ball_launch")
                """
                Duration, refer to log and video
                """
                pass
            case "ball_launch":
                self.transition("no_more_bet")
                """
                Duration, refer to log and video
                """
                pass
            case "no_more_bet":
                self.transition("winning_number")
                """
                Duration, refer to log and video
                """
                pass
            case "winning_number":
                self.transition("start_game")
                """
                Duration, refer to log and video
                """
                pass
            case "table_closed":
                self.transition("idle")
                """
                Duration, refer to log and video
                """
                pass

class RouletteSimulator(StateMachine):
    def __init__(self):
        super().__init__()
        self.masterRoulettePort, self.slaveRoulettePort = self.create_virtual_serial_port()
        self.thread = threading.Thread(target=self.roulette_main_thread, args=(self.masterRoulettePort,))
        self.thread.daemon = True
        self.thread.start()

    def create_virtual_serial_port(self):
        master, slave = pty.openpty()
        s_name = os.ttyname(slave)
        return master, s_name

    def state_discriminator(self,protocol_log_line):
        """
        When read one line of the protocol log, determine the current state of the roulette.
        """
        data = protocol_log_line
        if "*X:" in data:
            self.current_data_protocol_mode = "game_mode"

            if "*X:1" in data:
                self.game_state_transition_to("start_game")
            elif "*X:2" in data:
                self.game_state_transition_to("place_bet")
            elif "*X:3" in data:
                self.game_state_transition_to("ball_launch")
            elif "*X:4" in data:
                self.game_state_transition_to("no_more_bet")
            elif "*X:5" in data:
                self.game_state_transition_to("winning_number")
            elif "*X:6" in data:
                self.game_state_transition_to("table_closed")
            else:
                raise Exception("unknown game state.")
        elif "*o" in data:
            self.current_data_protocol_mode = "operation_mode"
            """
            Operation mode
            """
            pass
        elif "*F" in data:
            self.current_data_protocol_mode = "self_test_mode"
            """
            Self-test mode
            """
            pass
        elif "*P" in data:
            self.current_data_protocol_mode = "power_setting_mode"
            """
            Power setting mode
            """
            if "*P:1" in data:
                self.current_power_state = "on"
                """In arcade mode, power on will trigger table open"""
                self.game_state_transition_to("idle")
            elif "*P:0" in data:
                self.current_power_state = "off"
                """off will trigger table force close"""
                self.game_state_transition_to("table_closed")
        elif "*C" in data:
            self.current_data_protocol_mode = "calibration_mode"
            """
            Calibration mode
            """
            pass
        elif "*W" in data:
            self.current_data_protocol_mode = "warning_flag_mode"
            """
            Warning flag mode
            Restart the game
            """
            self.game_state_transition_to("start_game")
            pass
        elif "*M" in data:
            self.current_data_protocol_mode = "statistics_mode"
            """
            Statistics mode
            """
            pass
        else:
            raise Exception("unknown protocol log type.")

    def read_ss2_protocol_log(self,file_name,line_number):

        """
        This is a utility function to read the protocol log file.
        Should be moved to a utility module.
        """
        with open(file_name, "r") as file:
            line = next(islice(file, line_number - 1, line_number), None)
            return line if line else ""

    def roulette_state_display(self):
        print(f"Current game state: {self.current_game_state}")
        print(f"Current data protocol mode: {self.current_data_protocol_mode}")
        print(f"Current power state: {self.current_power_state}")

    def generate_protocol_data(self,mode):

        
        """
        This is a stateless protocol data generator, which means it does not consider the previous state of the roulette.
        When the stateful data generator has been implemented, this function should be removed.
        """

        """
        TODO:
        - The current protocol data only consider the *X command, need to add more types of commands, for example, 
            *o for operation mode
            *F for self-test mode
            *P for power setting
            *C for calibration
            *W for winning number statistics
            *M for pocket misfires statistics
        """

        match mode:
            case "X":

                """
                This part is to be deprecated when the stateful data generator is implemented.
                """

                game_states = list(range(1, 8))
                game_numbers = list(range(1,256))
                last_winning_numbers = list(range(0,37))
                warning_flags = list(range(0,16))
                rotor_speeds = list(range(10,541))
                rotor_directions = [0,1]

                game_state = random.choice(game_states)
                game_number = random.choice(game_numbers)
                last_winning_number = random.choice(last_winning_numbers)
                warning_flag = hex(random.choice(warning_flags))
                rotor_speed = random.choice(rotor_speeds)
                rotor_direction = random.choice(rotor_directions)

                return f"*X:{game_state:01d}:{game_number:03d}:{last_winning_number:02d}:{warning_flag}:{rotor_speed:03d}:{rotor_direction:01d}\r\n"

            case "o":
                """
                need to add the type behaviour of the operation mode here or in the casino_engineer_sim.py
                """
                pass
                return "*o\r\n"

            case "F":
                """
                need to add the type behaviour of the self-test mode here or in the casino_engineer_sim.py
                """
                pass
                return "*F\r\n"
            case "P":
                """
                need to add the type behaviour of the power setting mode here or in the casino_engineer_sim.py
                """
                pass
                return "*P\r\n"

            case "C":
                """
                need to add the type behaviour of the calibration mode here or in the casino_engineer_sim.py
                """
                pass
                return "*C\r\n"
            case "W":
                """
                need to add the type behaviour of the winning number statistics mode here or in the casino_engineer_sim.py
                """
                pass
                return "*W\r\n"
            case "M":
                """
                need to add the type behaviour of the pocket misfires statistics mode here or in the casino_engineer_sim.py
                """
                pass
                return "*M\r\n"
    
    def roulette_write_data_to_sdp(self,data):
        os.write(self.masterRoulettePort, data.encode())
        print(f"Roulette simulator sent to SDP: {data.decode().strip()}")

    def roulette_read_data_from_sdp(self):
        read_data = os.read(self.masterRoulettePort, 1024) # 1024 is the buffer size
        if read_data:
            print(f"Roulette supposed to be received from SDP: {read_data.decode().strip()}")

    def roulette_main_thread(self,master):

        line_number = 1

        
        while True:
            try:
                print("--------------before receive the next line of the log------------------")
                self.roulette_state_display()
                data = self.read_ss2_protocol_log(log_file_name,line_number)
                print("--------------after receive the next line of the log------------------")
                if not data:
                    print("Reached end of log file. Terminating program...")
                    os._exit(0) 
                else:

                    self.state_discriminator(data)
                    self.roulette_write_data_to_sdp(data)
                    self.roulette_read_data_from_sdp()
                    self.roulette_state_display()

                    line_number += 1
                    time.sleep(0.1) # the sleep time should be longer than the roulette's write interval

            except OSError:
                Exception("virtual serial main thread unexceptionally terminated.")
                break

if __name__ == "__main__":

    global log_file_name 
    log_file_name = "../log/ss2_protocol.log"

    roulette = RouletteSimulator()

    print(f"Roulette simulator is running. Virtual port: {roulette.slaveRoulettePort}")
    print("Press Ctrl+C to stop the simulator.")

    try:
        roulette.roulette_main_thread(roulette.masterRoulettePort)
        while True:
            pass # keep the thread alive
    except KeyboardInterrupt:
        print("Stopping roulette simulator...")
