import logging
import evdev
from typing import Optional, Callable
import threading
import time
import re


class HIDController:
    """Controller for HID devices (e.g., barcode scanner)"""

    def __init__(self, device_name: str = "Barcode Scanner"):
        self.device_name = device_name
        self.device = None
        self.running = True
        self.logger = logging.getLogger("HIDController")
        self.read_callback: Optional[Callable] = None
        self.read_thread = None
        self.scancodes = {
            # Mapping of USB HID scan codes to characters
            2: "1",
            3: "2",
            4: "3",
            5: "4",
            6: "5",
            7: "6",
            8: "7",
            9: "8",
            10: "9",
            11: "0",
            28: "\n",
            30: "A",
            31: "S",
            32: "D",
            33: "F",
            34: "G",
            35: "H",
            36: "J",
            37: "K",
            38: "L",
            39: ";",
            44: "Z",
            45: "X",
            46: "C",
            47: "V",
            48: "B",
            49: "N",
            50: "M",
        }

    def initialize(self) -> bool:
        """Initialize HID device connection"""
        try:
            devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
            for device in devices:
                if self.device_name.lower() in device.name.lower():
                    self.device = device
                    self.logger.info(f"Found device: {device.name}")
                    return True
            self.logger.error(f"No device found matching: {self.device_name}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to initialize HID device: {e}")
            return False

    def start_reading(self, callback: Callable):
        """Start reading thread with callback"""
        self.read_callback = callback
        self.read_thread = threading.Thread(target=self._read_loop)
        self.read_thread.daemon = True
        self.read_thread.start()

    def _read_loop(self):
        """Main reading loop"""
        if not self.device:
            return

        current_code = []
        try:
            for event in self.device.read_loop():
                if not self.running:
                    break

                if event.type == evdev.ecodes.EV_KEY:
                    data = evdev.categorize(event)
                    if data.keystate == 1:  # Key down
                        if data.scancode == 28:  # Enter key
                            if self.read_callback and current_code:
                                self.read_callback("".join(current_code))
                            current_code = []
                        elif data.scancode in self.scancodes:
                            current_code.append(self.scancodes[data.scancode])
        except Exception as e:
            self.logger.error(f"Error reading from HID device: {e}")

    def cleanup(self):
        """Cleanup resources"""
        self.running = False
        if self.device:
            self.device.close()

    @staticmethod
    def is_valid_card_code(code: str) -> bool:
        """Validate if the code matches playing card format"""
        # Example format: "H10" (Heart 10), "SA" (Spade Ace)
        pattern = r"^[HDCS][2-9TJQKA]$|^[HDCS]10$"
        return bool(re.match(pattern, code))

    @staticmethod
    def parse_card_code(code: str) -> tuple[Optional[str], Optional[str]]:
        """Parse card code into suit and value"""
        if not HIDController.is_valid_card_code(code):
            return None, None

        suit_map = {"H": "Hearts", "D": "Diamonds", "C": "Clubs", "S": "Spades"}
        value_map = {"T": "10", "J": "Jack", "Q": "Queen", "K": "King", "A": "Ace"}

        suit = suit_map.get(code[0])
        value = value_map.get(code[1], code[1:])

        return suit, value
