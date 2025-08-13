"""
Pytest configuration file for mocking hardware dependencies
"""

import pytest
from unittest.mock import MagicMock
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Mock serial port before importing main modules
@pytest.fixture(scope="session", autouse=True)
def mock_serial():
    """Mock serial port for testing environment"""
    import serial

    # Create a mock serial object
    mock_ser = MagicMock()
    mock_ser.port = "/dev/ttyUSB0"
    mock_ser.baudrate = 9600
    mock_ser.is_open = False
    mock_ser.in_waiting = 0
    mock_ser.write = MagicMock()
    mock_ser.readline = MagicMock(return_value=b"")
    mock_ser.close = MagicMock()

    # Mock the Serial class constructor
    def mock_serial_constructor(*args, **kwargs):
        return mock_ser

    # Store original and replace
    original_serial = serial.Serial
    serial.Serial = mock_serial_constructor

    yield mock_ser

    # Restore original Serial class
    serial.Serial = original_serial


@pytest.fixture(scope="session", autouse=True)
def mock_websockets():
    """Mock websockets for testing environment"""
    try:
        import websockets

        # Create a mock websocket connection
        mock_ws = MagicMock()
        mock_ws.send = MagicMock()
        mock_ws.recv = MagicMock(return_value="mock_response")

        # Mock the connect function to return a mock websocket
        async def mock_connect(uri):
            return mock_ws

        websockets.connect = mock_connect
    except ImportError:
        pass


@pytest.fixture(scope="session", autouse=True)
def mock_os_paths():
    """Mock OS paths that might not exist in test environment"""
    import os

    # Mock /dev/ttyUSB0
    if not os.path.exists("/dev/ttyUSB0"):
        # Create a temporary mock file
        os.makedirs("/tmp/mock_dev", exist_ok=True)
        with open("/tmp/mock_dev/ttyUSB0", "w") as f:
            f.write("mock")

        # Temporarily modify os.path.exists
        original_exists = os.path.exists

        def mock_exists(path):
            if path == "/dev/ttyUSB0":
                return True
            return original_exists(path)

        os.path.exists = mock_exists
