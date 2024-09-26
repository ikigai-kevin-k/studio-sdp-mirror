import threading
import queue
import time
import pty 
import os
import serial 
import random 
import tkinter as tk
from tkinter import ttk, scrolledtext

class GUI:
    def __init__(self, state_machine, los_comm, roulette_comm):
        self.root = tk.Tk()
        self.root.title("SDP Prototype Monitor")
        self.state_machine = state_machine
        self.los_comm = los_comm
        self.roulette_comm = roulette_comm
        self.message_queue = queue.Queue()

        self.setup_ui()

    def setup_ui(self):
        self.state_label = ttk.Label(self.root, text="Current State: IDLE")
        self.state_label.pack(pady=10)

        self.log_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=60, height=20)
        self.log_area.pack(padx=10, pady=10)

        self.command_entry = ttk.Entry(self.root, width=50)
        self.command_entry.pack(side=tk.LEFT, padx=10)

        self.send_button = ttk.Button(self.root, text="Send", command=self.send_command)
        self.send_button.pack(side=tk.LEFT)

    def send_command(self):
        command = self.command_entry.get()
        if self.los_comm:
            self.los_comm.command_queue.put(command)
        self.command_entry.delete(0, tk.END)

    def update_state(self, new_state):
        self.state_label.config(text=f"Current State: {new_state}")

    def add_message(self, message):
        self.message_queue.put(message)

    def update_log(self):
        while not self.message_queue.empty():
            message = self.message_queue.get()
            self.log_area.insert(tk.END, message + '\n')
            self.log_area.see(tk.END)
        self.root.after(100, self.update_log)

    def run(self):
        self.update_log()
        self.root.mainloop()


class SDPStateMachine:
    def __init__(self, gui=None):
        self.state = "IDLE"
        self.lock = threading.Lock()
        self.gui = gui
    
    def update_state(self, new_state):
        with self.lock:
            self.state = new_state
            print(f"SDP status updated as: {self.state}")
            if self.gui:
                self.gui.update_state(self.state)
                self.gui.add_message(f"SDP status updated as: {self.state}")


class WebSocketCommunication:
    def __init__(self, state_machine, roulette_comm):
        self.state_machine = state_machine
        self.roulette_comm = roulette_comm

    def start(self):
        print("WebSocket communication started")

    def send_message(self, message):
        print(f"WebSocket message sent: {message}")

class HTTPCommunication:
    def __init__(self, state_machine, roulette_comm):
        self.state_machine = state_machine
        self.roulette_comm = roulette_comm

    def start(self):
        print("HTTP server started")

    def handle_request(self, request):
        print(f"HTTP request handled: {request}")

class LOSCommunication:
    def __init__(self, state_machine, roulette_comm, gui=None):
        self.state_machine = state_machine
        self.roulette_comm = roulette_comm
        self.command_queue = queue.Queue()
        self.websocket_comm = WebSocketCommunication(state_machine, roulette_comm)
        self.http_comm = HTTPCommunication(state_machine, roulette_comm)
        self.gui = gui

    def start_communication(self):
        self.websocket_comm.start()
        self.http_comm.start()

    def listen_for_commands(self):
        while True:
            command = input("Enter LOS command (or 'websocket' or 'http'): ")
            if command.lower() == 'websocket':
                self.websocket_comm.send_message("Test WebSocket message")
            elif command.lower() == 'http':
                self.http_comm.handle_request("Test HTTP request")
            else:
                self.command_queue.put(command)

    def process_commands(self):
        while True:
            if not self.command_queue.empty():

                command = self.command_queue.get()
                message = f"Processing LOS commands: {command}"
                print(message)

                # Update state machine
                self.state_machine.update_state(f"PROCESSING_{command}")
                # forward to the roulette machine
                self.roulette_comm.send_command(command)

                if self.gui:
                    self.gui.add_message(message)

            time.sleep(0.1)



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
            time.sleep(0.01)  # low priority processing

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
    gui = GUI(None, None, None)  # temporary create GUI instance
    state_machine = SDPStateMachine(gui)
    los_comm = LOSCommunication(state_machine, None, gui)
    roulette_comm = RouletteCommunication(state_machine, los_comm, gui)
    los_comm.roulette_comm = roulette_comm

    gui.state_machine = state_machine
    gui.los_comm = los_comm
    gui.roulette_comm = roulette_comm

    roulette_comm.initialize_serial()
    los_comm.start_communication()

    # create and start threads
    threads = [
        threading.Thread(target=los_comm.process_commands),
        threading.Thread(target=roulette_comm.poll_roulette),
        threading.Thread(target=roulette_comm.process_polling_results)
    ]

    for thread in threads:
        thread.daemon = True
        thread.start()

    # run GUI
    print("Starting GUI...")
    gui.run()

    print("GUI closed. Cleaning up...")
    # clean up resources
    if roulette_comm.serial_port:
        roulette_comm.serial_port.close()
    if roulette_comm.master:
        os.close(roulette_comm.master)
    if roulette_comm.slave:
        os.close(roulette_comm.slave)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {e}")