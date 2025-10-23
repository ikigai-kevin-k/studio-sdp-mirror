"""
Pytest configuration file for mocking hardware dependencies
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
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
def mock_ws_client():
    """Mock WebSocket client for testing environment"""
    try:
        # Mock the SmartStudioWebSocketClient class
        from studio_api.ws_client import SmartStudioWebSocketClient

        # Create a mock client
        mock_client = MagicMock()
        mock_client.connect = AsyncMock(return_value=True)
        mock_client.disconnect = AsyncMock()
        mock_client.send_device_status = AsyncMock()
        mock_client.send_multiple_updates = AsyncMock()
        mock_client.send_status_update = AsyncMock()
        mock_client.get_server_preferences = MagicMock(
            return_value={
                "accepted_fields": [
                    "sdp",
                    "idp",
                    "shaker",
                    "broker",
                    "zCam",
                    "maintenance",
                ],
                "rejected_fields": [],
            }
        )
        mock_client.get_sent_updates_summary = MagicMock(
            return_value={"total_updates": 0, "updates": []}
        )

        # Store original and replace
        original_client = SmartStudioWebSocketClient
        SmartStudioWebSocketClient = MagicMock(return_value=mock_client)

        yield mock_client

        # Restore original class
        SmartStudioWebSocketClient = original_client

    except ImportError:
        # If ws_client module is not available, create a basic mock
        mock_client = MagicMock()
        mock_client.connect = AsyncMock(return_value=True)
        mock_client.disconnect = AsyncMock()
        mock_client.send_device_status = AsyncMock()
        mock_client.send_multiple_updates = AsyncMock()
        mock_client.send_status_update = AsyncMock()
        yield mock_client


@pytest.fixture(scope="session", autouse=True)
def mock_status_enums():
    """Mock status enums for testing environment"""
    try:
        from studio_api.ws_client import (
            StudioServiceStatusEnum,
            StudioMaintenanceStatusEnum,
        )

        # Mock the get_random_status methods
        StudioServiceStatusEnum.get_random_status = MagicMock(
            side_effect=["up", "down", "standby", "up", "down"]
        )
        StudioMaintenanceStatusEnum.get_random_status = MagicMock(
            return_value=False
        )

    except ImportError:
        # If ws_client module is not available, create basic mocks
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
