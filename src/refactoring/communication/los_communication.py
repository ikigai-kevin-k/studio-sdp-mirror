import queue
import time
from .websocket_communication import WebSocketCommunication
from .http_communication import HTTPCommunication

class LOSCommunication:
    def __init__(self, state_machine, roulette_comm, processors=None):
        self.state_machine = state_machine
        self.roulette_comm = roulette_comm
        self.processors = processors or []
        self.command_queue = queue.Queue()
        self.websocket_comm = WebSocketCommunication(state_machine, roulette_comm) # no need to implement yet
        self.http_comm = HTTPCommunication(state_machine, roulette_comm)

    def add_processor(self, processor):
        self.processors.append(processor)

    def start_communication(self):
        self.websocket_comm.start() # no need to implement yet
        self.http_comm.start()

    def process_commands(self):
        while True:
            if not self.command_queue.empty():
                command = self.command_queue.get()
                print(f"Processing LOS command: {command}")
                for processor in self.processors:
                    processor.process_data() # not implemented yet
            time.sleep(0.1)

    def handle_websocket_message(self, message): # no need to implement yet
        for processor in self.processors:
            processor.handle_websocket_message(message)

    def handle_http_request(self, request):
        # refer to sim/SDP_client_sim.py for implementation
        for processor in self.processors:
            processor.handle_http_request(request)

