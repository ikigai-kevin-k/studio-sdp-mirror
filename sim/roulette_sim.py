import serial
import time
import os
import pty
import threading
import random
from itertools import islice
import sys
def create_virtual_serial_port():
    master, slave = pty.openpty()
    s_name = os.ttyname(slave)
    return master, s_name

def generate_protocol_data():

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

    # return f"*X:{x:01d}:{y:03d}:{z:02d}:{a}:{b:03d}:{c:01d}\r\n"
    return f"*X:{game_state:01d}:{game_number:03d}:{last_winning_number:02d}:{warning_flag}:{rotor_speed:03d}:{rotor_direction:01d}\r\n"

def read_ss2_protocol_log(line_number):

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
        # print(f"Read line {line_number}: {line}")
        return line if line else ""

BIG_NUMBER = 1000000

def virtual_serial_thread(master):
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

if __name__ == "__main__":
    
    masterRoulettePort, slaveRoulettePort = create_virtual_serial_port()
    print(f"Created virtual serial port: {slaveRoulettePort}")
    print("masterRoulettePort: ", masterRoulettePort)
    
    thread = threading.Thread(target=virtual_serial_thread, args=(masterRoulettePort,))
    thread.daemon = True
    thread.start()

    print(f"Roulette simulator is running. Virtual port: {slaveRoulettePort}")
    print("Press Ctrl+C to stop the simulator.")

    try:
        while True:
            pass # keep the thread alive
    except KeyboardInterrupt:
        print("Stopping roulette simulator...")
