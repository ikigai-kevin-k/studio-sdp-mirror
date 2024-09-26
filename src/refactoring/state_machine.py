import threading

class SDPStateMachine:
    def __init__(self, gui=None):
        self.state = "IDLE"
        self.lock = threading.Lock()
        self.gui = gui
        if self.gui:
            self.gui.add_message("State Machine initialized")
    
    def update_state(self, new_state):
        with self.lock:
            self.state = new_state
            message = f"SDP status updated as: {self.state}"
            print(message)
            if self.gui:
                self.gui.update_state(self.state)
                self.gui.add_message(message)
