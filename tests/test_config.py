"""
Test configuration and utilities for WebSocket testing.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import mock_open


class TestConfig:
    """Test configuration utilities."""

    @staticmethod
    def create_mock_ws_config():
        """Create a mock WebSocket configuration for testing."""
        return {
            "server_url": "ws://test-server:8082",
            "device_name": "testDevice",
            "token": "test-token",
            "tables": [
                {"table_id": "SBO-001", "name": "SBO-001"},
                {"table_id": "ARO-001", "name": "ARO-001"},
                {"table_id": "ARO-002", "name": "ARO-002"},
            ],
        }

    @staticmethod
    def create_temp_config_file(config_data=None):
        """Create a temporary configuration file for testing."""
        if config_data is None:
            config_data = TestConfig.create_mock_ws_config()

        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        json.dump(config_data, temp_file)
        temp_file.close()

        return temp_file.name

    @staticmethod
    def cleanup_temp_config_file(file_path):
        """Clean up a temporary configuration file."""
        try:
            Path(file_path).unlink()
        except FileNotFoundError:
            pass


class MockWebSocketClient:
    """Mock WebSocket client for testing."""

    def __init__(self):
        self.connected = False
        self.sent_messages = []
        self.received_messages = []
        self.accepted_fields = set()
        self.rejected_fields = set()

    async def connect(self):
        """Mock connection method."""
        self.connected = True
        return True

    async def disconnect(self):
        """Mock disconnection method."""
        self.connected = False

    async def send_device_status(self, device, status):
        """Mock sending device status."""
        if self.connected:
            message = {"device": device, "status": status}
            self.sent_messages.append(message)
            self.accepted_fields.add(device)
            return True
        return False

    async def send_multiple_updates(self, updates):
        """Mock sending multiple updates."""
        if self.connected:
            for device, status in updates.items():
                await self.send_device_status(device, status)
            return True
        return False

    async def send_status_update(self, status_data):
        """Mock sending status update."""
        if self.connected:
            self.sent_messages.append(status_data)
            return True
        return False

    def get_server_preferences(self):
        """Mock getting server preferences."""
        return {
            "accepted_fields": list(self.accepted_fields),
            "rejected_fields": list(self.rejected_fields),
        }

    def get_sent_updates_summary(self):
        """Mock getting sent updates summary."""
        return {
            "total_updates": len(self.sent_messages),
            "updates": self.sent_messages,
        }


class MockStatusEnums:
    """Mock status enums for testing."""

    class StudioServiceStatusEnum:
        """Mock service status enum."""

        UP = "up"
        DOWN = "down"
        STANDBY = "standby"
        CALIBRATION = "calibration"
        EXCEPTION = "exception"

        @classmethod
        def get_random_status(cls):
            """Get a random status."""
            import random

            return random.choice([cls.UP, cls.DOWN, cls.STANDBY])

    class StudioMaintenanceStatusEnum:
        """Mock maintenance status enum."""

        TRUE = True
        FALSE = False

        @classmethod
        def get_random_status(cls):
            """Get a random maintenance status."""
            import random

            return random.choice([cls.TRUE, cls.FALSE])


def mock_file_operations():
    """Create mock file operations for testing."""
    mock_config = TestConfig.create_mock_ws_config()

    # Mock open function
    mock_file = mock_open(read_data=json.dumps(mock_config))

    return mock_file, mock_config


def create_test_environment():
    """Create a complete test environment."""
    return {
        "config": TestConfig.create_mock_ws_config(),
        "client": MockWebSocketClient(),
        "enums": MockStatusEnums(),
        "temp_files": [],
    }


def cleanup_test_environment(env):
    """Clean up test environment."""
    for temp_file in env.get("temp_files", []):
        TestConfig.cleanup_temp_config_file(temp_file)
