from abc import ABC, abstractmethod

class DataProcessor(ABC):
    def __init__(self, state_machine, los_comm):
        self.state_machine = state_machine
        self.los_comm = los_comm

    @abstractmethod
    def initialize(self):
        pass

    @abstractmethod
    def process_data(self):
        pass

    @abstractmethod
    def handle_websocket_message(self, message):
        pass

    @abstractmethod
    def handle_http_request(self, request):
        pass