class HTTPCommunication:
    def __init__(self, state_machine, roulette_comm):
        self.state_machine = state_machine
        self.roulette_comm = roulette_comm

    def start(self):
        print("HTTP server started")

    def handle_request(self, request):
        print(f"HTTP request handled: {request}")
