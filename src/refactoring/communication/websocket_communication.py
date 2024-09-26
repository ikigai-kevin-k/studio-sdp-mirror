class WebSocketCommunication:
    def __init__(self, state_machine, roulette_comm):
        self.state_machine = state_machine
        self.roulette_comm = roulette_comm

    def start(self):
        print("WebSocket communication started")

    def send_message(self, message):
        print(f"WebSocket message sent: {message}")
