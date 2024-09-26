import tkinter as tk
from tkinter import ttk, scrolledtext
import queue

class GUI:
    def __init__(self, state_machine, los_comm, roulette_comm):
        self.root = tk.Tk()
        self.root.title("SDP Prototype Monitor")
        self.state_machine = state_machine
        self.los_comm = los_comm
        self.roulette_comm = roulette_comm
        self.message_queue = queue.Queue()

        self.setup_ui()
        self.add_message("GUI initialized")
        self.add_message("Waiting for system messages...")

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
        print("Updating log...")  # Added this line
        while not self.message_queue.empty():
            message = self.message_queue.get()
            print(f"Adding message to log: {message}")  # Added this line
            self.log_area.insert(tk.END, message + '\n')
            self.log_area.see(tk.END)
        self.root.after(100, self.update_log)

    def run(self):
        self.update_log()
        self.add_message("GUI is running")
        self.root.mainloop()
