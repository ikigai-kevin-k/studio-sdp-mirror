import serial
import threading
import time
from datetime import datetime
from typing import Optional, Callable
import logging
import subprocess

class SerialController:
    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.serial_port = None
        self.running = True
        self.logger = logging.getLogger("SerialController")
        self.read_callback: Optional[Callable] = None
        self.read_thread = None

    def initialize(self):
        """Initialize serial port connection"""
        try:
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=1
            )
            self.logger.info(f"Successfully opened serial port {self.port}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to open serial port: {e}")
            return False

    def start_reading(self, callback: Callable):
        """Start reading thread with callback"""
        self.read_callback = callback
        self.read_thread = threading.Thread(target=self._read_loop)
        self.read_thread.daemon = True
        self.read_thread.start()

    def _read_loop(self):
        """Main reading loop"""
        while self.running and self.serial_port:
            try:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.readline().decode('utf-8').strip()
                    if self.read_callback:
                        self.read_callback(data)
            except Exception as e:
                self.logger.error(f"Error reading from serial port: {e}")
            time.sleep(0.1)

    def write(self, data: str):
        """Write data to serial port"""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.write((data + '\r\n').encode())
                return True
        except Exception as e:
            self.logger.error(f"Error writing to serial port: {e}")
        return False

    def send_command_and_wait(self, command: str, timeout: int = 2) -> Optional[str]:
        """Send command and wait for response"""
        if not self.write(command):
            return None

        cmd_type = command[-1].lower()
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            if self.serial_port.in_waiting > 0:
                response = self.serial_port.readline().decode('utf-8').strip()
                if response.startswith(f"*T {cmd_type}"):
                    parts = response.split()
                    if len(parts) > 2:
                        return ' '.join(parts[2:])
            time.sleep(0.1)
        return None

    def cleanup(self):
        """Cleanup resources"""
        self.running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()

    @staticmethod
    def check_serial_port(port: str) -> bool:
        """Check if serial port is available"""
        try:
            result = subprocess.run(['lsof', port], capture_output=True, text=True)
            return not bool(result.stdout)
        except Exception:
            return False

    @staticmethod
    def list_available_ports() -> list[str]:
        """List all available serial ports"""
        try:
            import serial.tools.list_ports
            return [port.device for port in serial.tools.list_ports.comports()]
        except Exception:
            return []
