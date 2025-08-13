import os
import time
import logging
import logging.handlers
from utils import ensure_directory_exists, get_timestamp

# Color constants
RED = "\033[91m"
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
GRAY = "\033[90m"
RESET = "\033[0m"


class ColorfulLogger(logging.Logger):
    def __init__(self, name: str):
        super().__init__(name=name)

        # Setup terminal handler
        terminal_handler = logging.StreamHandler()
        terminal_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        terminal_handler.setFormatter(terminal_formatter)

        # Setup terminal output log file handler
        terminal_file_handler = logging.FileHandler("./terminal_output.log", mode="w")
        terminal_file_handler.setFormatter(terminal_formatter)

        # Setup serial data log file handler
        serial_file_handler = logging.FileHandler("./serial_data.log", mode="w")
        serial_file_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))

        # Setup logger
        self.setLevel(logging.INFO)
        self.addHandler(terminal_handler)
        self.addHandler(terminal_file_handler)

        # Create serial data specific logger
        self.serial_logger = logging.getLogger("serial_logger")
        self.serial_logger.setLevel(logging.INFO)
        self.serial_logger.addHandler(serial_file_handler)

    def log_with_color(self, message: str, color: str = ""):
        self.info(f"{color}{message}{RESET}")

    def log_serial_data(self, message: str):
        self.serial_logger.info(message)


def setup_logging(enable_logging: bool, log_dir: str) -> None:
    """Setup logging configuration"""
    if enable_logging:
        ensure_directory_exists(log_dir)
        configure_logging(log_dir)


def configure_logging(log_dir: str) -> None:
    """Configure logging handlers and formatters"""
    # ... (existing logging configuration code) ...


def get_logger(name: str) -> logging.Logger:
    """Get logger instance with specified name"""
    return logging.getLogger(name)
