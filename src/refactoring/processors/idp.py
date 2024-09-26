from .data_processor import DataProcessor

class IDP(DataProcessor):
    def __init__(self, state_machine, los_comm):
        super().__init__(state_machine, los_comm)
        # IDP specific attributes can be initialized here

    def initialize(self):
        # implement IDP initialization logic
        pass

    def process_data(self):
        # implement IDP data processing logic
        pass

    def handle_websocket_message(self, message):
        # implement IDP WebSocket message processing logic
        pass

    def handle_http_request(self, request):
        # implement IDP HTTP request processing logic
        pass