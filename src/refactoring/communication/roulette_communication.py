import queue
import time
import pty
import os
import serial
import random

class RouletteCommunication:
    def __init__(self, state_machine, los_comm, gui=None):
        self.state_machine = state_machine
        self.los_comm = los_comm
        self.gui = gui
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
                    # Write command to be seperated from here to a mocked roulette machine in the future.
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
                    error_message = f"Serial communication error: {e}"
                    print(error_message)
                    if self.gui:
                        self.gui.add_message(error_message)
            time.sleep(0.1)  # Poll every 0.1 seconds

    def process_polling_results(self):
        while True:
            if not self.polling_results.empty():
                result = self.polling_results.get()
                message = f"Processing roulette polling results: {result}"
                print(message)
                if self.gui:
                    self.gui.add_message(message)
                # parse result
                parsed_result = self.parse_result(result)
                # update state machine
                self.state_machine.update_state(f"ROULETTE_{parsed_result}")
            time.sleep(0.1)  # low priority processing

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
