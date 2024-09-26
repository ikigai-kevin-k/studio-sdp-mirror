from .data_processor import DataProcessor

class SDP(DataProcessor):
    def __init__(self, state_machine, los_comm, roulette_comm):
        super().__init__(state_machine, los_comm)
        self.roulette_comm = roulette_comm

    def initialize(self):
        # implement SDP initialization logic
        pass

    def process_data(self):
        # implement SDP data processing logic
        pass

    def handle_websocket_message(self, message):
        # implement SDP WebSocket message processing logic
        pass

    def handle_http_request(self, request):
        # implement SDP HTTP request processing logic
        pass
