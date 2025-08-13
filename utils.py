import serial
import asyncio
import json
import subprocess
from typing import Tuple, Dict, Any, Optional
import os
import logging
from datetime import datetime
from los_api.sb.api_v2_sb import get_roundID_v2


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file"""
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        raise Exception(f"Failed to load config file: {e}")


def check_process_exists(process_name: str) -> bool:
    """Check if a process exists by name"""
    try:
        output = subprocess.check_output(["pgrep", "-f", process_name])
        return bool(output)
    except subprocess.CalledProcessError:
        return False


def ensure_directory_exists(path: str) -> None:
    """Ensure directory exists, create if not"""
    if not os.path.exists(path):
        os.makedirs(path)


def get_timestamp() -> str:
    """Get current timestamp in formatted string"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def parse_command_args(command: str) -> tuple[str, list[str]]:
    """Parse command and its arguments"""
    parts = command.split()
    return parts[0], parts[1:] if len(parts) > 1 else []


def validate_numeric_range(value: float, min_val: float, max_val: float) -> bool:
    """Validate if a numeric value is within range"""
    return min_val <= value <= max_val


def format_log_message(level: str, message: str) -> str:
    """Format log message with timestamp and level"""
    timestamp = get_timestamp()
    return f"[{timestamp}] {level}: {message}"


def safe_cast(value: str, to_type: type, default: Any = None) -> Any:
    """Safely cast value to specified type"""
    try:
        return to_type(value)
    except (ValueError, TypeError):
        return default


def check_serial_port(port: str) -> bool:
    """Check if serial port is available"""
    try:
        result = subprocess.run(["lsof", port], capture_output=True, text=True)
        return not bool(result.stdout)
    except Exception:
        return False


def setup_serial_port(port: str, baudrate: int) -> serial.Serial:
    """Setup and return serial port connection"""
    return serial.Serial(
        port=port,
        baudrate=baudrate,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1,
    )


async def check_los_state(url: str, token: str) -> Tuple[int, str, str]:
    """Check LOS system state"""
    try:
        return get_roundID_v2(url, token)
    except Exception as e:
        raise Exception(f"Failed to get LOS state: {e}")


def create_los_urls(base_url: str, game_code: str) -> Tuple[str, str]:
    """Create LOS API URLs"""
    get_url = f"{base_url}/v1/service/table/{game_code}"
    post_url = f"{base_url}/v1/service/sdp/table/{game_code}"
    return get_url, post_url


# ANSI escape codes for colors
RED = "\033[91m"
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RESET = "\033[0m"


def log_with_color(message, color=None):
    """Print log message with color"""
    if color:
        print(f"{color}{message}{RESET}")
    else:
        print(message)
