import logging
from typing import Optional, Callable
import evdev
import re
import threading
from proto.hid import HIDController

class BarcodeScannerController(HIDController):
    """Controller for barcode scanner device"""
    def __init__(self, device_name: str = "Barcode Scanner"):
        super().__init__(device_name)
        self.barcode_pattern = re.compile(r'^[A-Z0-9]+$')
        self.card_pattern = re.compile(r'^[HDCS][2-9TJQKA]$|^[HDCS]10$')

    def is_valid_barcode(self, code: str) -> bool:
        """Validate barcode format"""
        return bool(self.barcode_pattern.match(code))

    def parse_barcode(self, code: str) -> Optional[str]:
        """Parse and validate barcode"""
        if self.is_valid_barcode(code):
            return code.strip()
        return None

    def start_reading(self, callback: Callable):
        """Start reading barcodes with callback"""
        super().start_reading(self._handle_barcode)
        self.read_callback = callback

    def _handle_barcode(self, code: str):
        """Handle scanned barcode"""
        parsed_code = self.parse_barcode(code)
        if parsed_code and self.read_callback:
            self.read_callback(parsed_code)
        else:
            self.logger.warning(f"Invalid barcode scanned: {code}")
