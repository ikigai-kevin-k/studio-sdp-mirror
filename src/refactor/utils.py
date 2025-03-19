import serial
import asyncio
import json
from typing import Tuple, Dict, Any
from los_api.api import get_roundID

def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        raise Exception(f"Failed to load config file: {e}")

def check_serial_port(port: str) -> bool:
    """Check if serial port is available"""
    try:
        import subprocess
        result = subprocess.run(['lsof', port], capture_output=True, text=True)
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
        timeout=1
    )

async def check_los_state(url: str, token: str) -> Tuple[int, str, str]:
    """Check LOS system state"""
    try:
        return get_roundID(url, token)
    except Exception as e:
        raise Exception(f"Failed to get LOS state: {e}")

def create_los_urls(base_url: str, game_code: str) -> Tuple[str, str]:
    """Create LOS API URLs"""
    get_url = f"{base_url}/v1/service/table/{game_code}"
    post_url = f"{base_url}/v1/service/sdp/table/{game_code}"
    return get_url, post_url
