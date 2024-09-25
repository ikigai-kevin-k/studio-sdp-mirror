import threading
import queue
import time

class SDPStateMachine:
    def __init__(self):
        self.state = "IDLE"
    
    def update_state(self, new_state):
        self.state = new_state
        print(f"SDP state updated to: {self.state}")

class LOSCommunication:
    def __init__(self, state_machine, roulette_comm):
        self.state_machine = state_machine
        self.roulette_comm = roulette_comm
        self.command_queue = queue.Queue()

    def listen_for_commands(self):
        while True:
            # Simulate receiving LOS commands
            command = input("Enter LOS command: ")
            self.command_queue.put(command)

    def process_commands(self):
        while True:
            if not self.command_queue.empty():
                command = self.command_queue.get()
                print(f"Processing LOS command: {command}")
                # Update state machine
                self.state_machine.update_state(f"PROCESSING_{command}")
                # Forward to roulette machine
                self.roulette_comm.send_command(command)

class RouletteCommunication:
    def __init__(self, state_machine, los_comm):
        self.state_machine = state_machine
        self.los_comm = los_comm
        self.polling_results = queue.Queue()

    def poll_roulette(self):
        while True:
            # Simulate roulette machine polling
            result = input("Enter roulette polling result: ")
            self.polling_results.put(result)

    def process_polling_results(self):
        while True:
            if not self.polling_results.empty():
                result = self.polling_results.get()
                print(f"Processing roulette polling result: {result}")
                # Update state machine
                self.state_machine.update_state(f"ROULETTE_{result}")
                # Forward back to LOS if necessary
                # self.los_comm.send_result(result)

    def send_command(self, command):
        print(f"Sending command to roulette machine: {command}")

def main():
    state_machine = SDPStateMachine()
    roulette_comm = RouletteCommunication(state_machine, None)
    los_comm = LOSCommunication(state_machine, roulette_comm)
    roulette_comm.los_comm = los_comm

    # Create and start threads
    threads = [
        threading.Thread(target=los_comm.listen_for_commands),
        threading.Thread(target=los_comm.process_commands),
        threading.Thread(target=roulette_comm.poll_roulette),
        threading.Thread(target=roulette_comm.process_polling_results)
    ]

    for thread in threads:
        thread.start()

    # Main loop
    while True:
        print(f"Current SDP state: {state_machine.state}")
        time.sleep(5)  # Print state every 5 seconds

if __name__ == "__main__":
    main()