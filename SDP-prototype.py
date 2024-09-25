import threading
import queue
import time
import pty 
import os
import serial 
import random 

class SDPStateMachine:
    def __init__(self):
        self.state = "IDLE"
        self.lock = threading.Lock()
    
    def update_state(self, new_state):
        with self.lock:
            self.state = new_state
            print(f"SDP status updated as: {self.state}")

class LOSCommunication:
    def __init__(self, state_machine, roulette_comm):
        self.state_machine = state_machine
        self.roulette_comm = roulette_comm
        self.command_queue = queue.Queue()

    def listen_for_commands(self):
        while True:
            # Simulate receiving LOS command events
            command = input("Enter LOS command events: ")
            self.command_queue.put(command)

    def process_commands(self):
        while True:
            if not self.command_queue.empty():
                command = self.command_queue.get()
                print(f"Processing LOS commands: {command}")
                # Update state machine
                self.state_machine.update_state(f"PROCESSING_{command}")
                # forward to the roulette machine
                self.roulette_comm.send_command(command)
            # high priority processing, short sleep
            time.sleep(0.1)

class RouletteCommunication:
    def __init__(self, state_machine, los_comm):
        self.state_machine = state_machine
        self.los_comm = los_comm
        self.serial_port = None
        self.polling_results = queue.Queue()
        self.master, self.slave = None, None

    def initialize_serial(self):
        # Create a virtual serial port
        self.master, self.slave = pty.openpty()
        slave_name = os.ttyname(self.slave)
        print(f"Created virtual serial port: {slave_name}")

        # Initialize serial communication using the virtual port
        self.serial_port = serial.Serial(slave_name, 9600, timeout=1,
                                         parity=serial.PARITY_NONE,
                                         stopbits=serial.STOPBITS_ONE,
                                         bytesize=serial.EIGHTBITS)
        print("Serial port initialized successfully")

    def poll_roulette(self):
        while True:
            if self.serial_port:
                try:
                    # Send polling command
                    self.serial_port.write(b'*X:1:000:25:0:000:0\r\n')
                    # Read response
                    response = self.serial_port.readline().decode().strip()
                    if response:
                        self.polling_results.put(response)
                    else:
                        # Simulate a response if none is received
                        simulated_response = f"*X:1:{random.randint(100,999)}:25:0:{random.randint(100,999)}:0"
                        self.polling_results.put(simulated_response)
                except serial.SerialException as e:
                    print(f"Serial communication error: {e}")
            time.sleep(0.5)  # Poll every 0.5 seconds

    def process_polling_results(self):
        while True:
            if not self.polling_results.empty():
                result = self.polling_results.get()
                print(f"processing roulette polling results: {result}")
                # parse result
                parsed_result = self.parse_result(result)
                # update state machine
                self.state_machine.update_state(f"ROULETTE_{parsed_result}")
                # forward back to LOS
                # self.los_comm.send_result(parsed_result)
            time.sleep(0.2)  # low priority processing

    def parse_result(self, result):
        # parsing game protocol result
        # example: *X:1:400:25:0:441:0
        parts = result.split(':')
        if len(parts) == 7 and parts[0] == '*X':
            return f"ID_{parts[1]}_DATA_{parts[5]}"
        return "Mocked Roulette Results"

    def send_command(self, command):
        if self.serial_port:
            try:
                # transform LOS command to game protocol format
                formatted_command = self.format_command(command)
                self.serial_port.write(formatted_command.encode() + b'\r\n')
                print(f"send command to roulette machine: {formatted_command}")
            except serial.SerialException as e:
                print(f"send command error: {e}")

    def format_command(self, command):
        # transform LOS command to game protocol format
        # example: transform "START_GAME" to "*X:1:100:25:0:000:0"
        # need to be adjusted according to actual LOS command and game protocol
        return f"*X:1:100:25:0:000:0"

def main():
    state_machine = SDPStateMachine()
    roulette_comm = RouletteCommunication(state_machine, None)
    los_comm = LOSCommunication(state_machine, roulette_comm)
    roulette_comm.los_comm = los_comm

    roulette_comm.initialize_serial()

    # Create and start threads
    threads = [
        threading.Thread(target=los_comm.listen_for_commands),
        threading.Thread(target=los_comm.process_commands),
        threading.Thread(target=roulette_comm.poll_roulette),
        threading.Thread(target=roulette_comm.process_polling_results)
    ]

    for thread in threads:
        thread.daemon = True
        thread.start()

    # Main loop
    try:
        while True:
            print(f"Current SDP state: {state_machine.state}")
            time.sleep(5)  # Print state every 5 seconds
    except KeyboardInterrupt:
        print("Program terminated")
    finally:
        if roulette_comm.serial_port:
            roulette_comm.serial_port.close()
        if roulette_comm.master:
            os.close(roulette_comm.master)
        if roulette_comm.slave:
            os.close(roulette_comm.slave)

if __name__ == "__main__":
    main()