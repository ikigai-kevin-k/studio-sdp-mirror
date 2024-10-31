import time
import os
import pty
import threading
import random
from itertools import islice

class RouletteSimulator:
    def __init__(self):
        self.masterRoulettePort, self.slaveRoulettePort = self.create_virtual_serial_port()
        self.thread = threading.Thread(target=self.virtual_serial_thread, args=(self.masterRoulettePort,))
        self.thread.daemon = True
        self.thread.start()

    def create_virtual_serial_port(self):
        master, slave = pty.openpty()
        s_name = os.ttyname(slave)
        return master, s_name

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
    def virtual_serial_thread(self, master):
        line_number = 1
        while True:
            try:

                data = read_ss2_protocol_log(line_number)
                
                if not data:
                    print("Reached end of log file. Terminating program...")
                    os._exit(0) 

                data = data.encode()
                line_number += 1
                
                os.write(master, data)
                print(f"Roulette simulator sent: {data.decode().strip()}")

                read_data = os.read(master, 1024) # 1024 is the buffer size
                if read_data:
                    print(f"SDP supposed to be received: {read_data.decode().strip()}")

                    """
                    TODO:
                    - The logic of processing the received data and update the simulator's state
                    """

                time.sleep(0.1) # the sleep time should be longer than the roulette's write interval

            except OSError:
                break

def read_ss2_protocol_log(line_number):

    """
    This is a utility function to read the protocol log file.
    Should be moved to a utility module.
    """

    """
    TODO:
    - The current protocol log only consider the *X command, need to consider more types of commands:
        *o for operation mode
        *F for self-test mode
        *P for power setting
        *C for calibration
        *W for winning number statistics
        *M for pocket misfires statistics
    """
    with open("./log/ss2_protocol.log", "r") as file:
        line = next(islice(file, line_number - 1, line_number), None)
        return line if line else ""

BIG_NUMBER = 1000000



if __name__ == "__main__":
    
    roulette = RouletteSimulator()

    print(f"Roulette simulator is running. Virtual port: {roulette.slaveRoulettePort}")
    print("Press Ctrl+C to stop the simulator.")

    try:
        while True:
            pass # keep the thread alive
    except KeyboardInterrupt:
        print("Stopping roulette simulator...")
