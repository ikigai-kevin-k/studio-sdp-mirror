"""
Unit tests for ws_sb.py module.

This module tests the WebSocket device info functionality for SBO-001 table.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path

# Import the module to test
from studio_api.ws_sb import test_sbo_001_device_info, main


class TestWsSbModule:
    """Test cases for ws_sb module."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration data."""
        return {
            "server_url": "ws://test-server:8082",
            "device_name": "testDevice",
            "token": "test-token",
            "tables": [
                {"table_id": "SBO-001", "name": "SBO-001"},
                {"table_id": "ARO-001", "name": "ARO-001"},
            ],
        }

    @pytest.fixture
    def mock_ws_client(self):
        """Mock WebSocket client."""
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
            return_value={
                "total_updates": 6,
                "updates": [
                    {"data": {"sdp": "up"}},
                    {"data": {"idp": "up"}},
                    {"data": {"shaker": "up"}},
                    {"data": {"broker": "up"}},
                    {"data": {"zCam": "up"}},
                    {"data": {"maintenance": False}},
                ],
            }
        )
        return mock_client

    @pytest.fixture
    def mock_status_enums(self):
        """Mock status enums."""
        mock_service_enum = MagicMock()
        mock_service_enum.get_random_status = MagicMock(
            side_effect=["up", "down", "standby", "up", "down"]
        )

        mock_maintenance_enum = MagicMock()
        mock_maintenance_enum.get_random_status = MagicMock(return_value=False)

        return mock_service_enum, mock_maintenance_enum

    @patch("studio_api.ws_sb.SmartStudioWebSocketClient")
    @patch("studio_api.ws_sb.StudioServiceStatusEnum")
    @patch("studio_api.ws_sb.StudioMaintenanceStatusEnum")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("os.path.join")
    async def test_test_sbo_001_device_info_success(
        self,
        mock_join,
        mock_json_load,
        mock_open_file,
        mock_maintenance_enum,
        mock_service_enum,
        mock_client_class,
        mock_config,
    ):
        """Test successful execution of test_sbo_001_device_info."""
        # Setup mocks
        mock_join.return_value = "/mock/path/conf/ws.json"
        mock_json_load.return_value = mock_config
        mock_client_class.return_value = mock_client_class.return_value

        # Mock the client instance
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
            return_value={"total_updates": 6, "updates": []}
        )
        mock_client_class.return_value = mock_client

        # Mock status enums
        mock_service_enum.get_random_status = MagicMock(
            side_effect=["up", "down", "standby", "up", "down"]
        )
        mock_maintenance_enum.get_random_status = MagicMock(return_value=False)

        # Execute function
        await test_sbo_001_device_info()

        # Verify client was created with correct parameters
        mock_client_class.assert_called_once_with(
            mock_config["server_url"],
            "SBO-001",
            mock_config["device_name"],
            mock_config["token"],
        )

        # Verify connection was attempted
        mock_client.connect.assert_called_once()

        # Verify device status updates were sent
        assert (
            mock_client.send_device_status.call_count >= 5
        )  # At least 5 device status updates

        # Verify disconnect was called
        mock_client.disconnect.assert_called_once()

    @patch(
        "builtins.open", side_effect=FileNotFoundError("Config file not found")
    )
    async def test_test_sbo_001_device_info_config_file_not_found(
        self, mock_open_file
    ):
        """Test handling of missing configuration file."""
        # Execute function - should handle FileNotFoundError gracefully
        await test_sbo_001_device_info()

        # Verify file was attempted to be opened
        mock_open_file.assert_called_once()

    @patch("builtins.open", new_callable=mock_open)
    @patch(
        "json.load",
        side_effect=json.JSONDecodeError("Invalid JSON", "content", 0),
    )
    async def test_test_sbo_001_device_info_invalid_json(
        self, mock_json_load, mock_open_file
    ):
        """Test handling of invalid JSON in configuration file."""
        # Execute function - should handle JSONDecodeError gracefully
        await test_sbo_001_device_info()

        # Verify JSON was attempted to be loaded
        mock_json_load.assert_called_once()

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    async def test_test_sbo_001_device_info_missing_key(
        self, mock_json_load, mock_open_file
    ):
        """Test handling of missing configuration keys."""
        # Setup mock to return config with missing key
        mock_config = {
            "server_url": "ws://test-server:8082"
        }  # Missing device_name and token
        mock_json_load.return_value = mock_config

        # Execute function - should handle KeyError gracefully
        await test_sbo_001_device_info()

        # Verify JSON was loaded
        mock_json_load.assert_called_once()

    @patch("studio_api.ws_sb.SmartStudioWebSocketClient")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("os.path.join")
    async def test_test_sbo_001_device_info_connection_failed(
        self,
        mock_join,
        mock_json_load,
        mock_open_file,
        mock_client_class,
        mock_config,
    ):
        """Test handling of failed WebSocket connection."""
        # Setup mocks
        mock_join.return_value = "/mock/path/conf/ws.json"
        mock_json_load.return_value = mock_config

        # Mock the client instance with failed connection
        mock_client = MagicMock()
        mock_client.connect = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        # Execute function
        await test_sbo_001_device_info()

        # Verify connection was attempted
        mock_client.connect.assert_called_once()

        # Verify no device status updates were sent
        mock_client.send_device_status.assert_not_called()

    @patch("studio_api.ws_sb.SmartStudioWebSocketClient")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("os.path.join")
    async def test_test_sbo_001_device_info_exception_handling(
        self,
        mock_join,
        mock_json_load,
        mock_open_file,
        mock_client_class,
        mock_config,
    ):
        """Test exception handling during execution."""
        # Setup mocks
        mock_join.return_value = "/mock/path/conf/ws.json"
        mock_json_load.return_value = mock_config

        # Mock the client instance that raises an exception
        mock_client = MagicMock()
        mock_client.connect = AsyncMock(
            side_effect=Exception("Connection error")
        )
        mock_client_class.return_value = mock_client

        # Execute function - should handle exception gracefully
        await test_sbo_001_device_info()

        # Verify connection was attempted
        mock_client.connect.assert_called_once()

    def test_main_function_exists(self):
        """Test that the main function exists and is callable."""
        # Verify main function exists
        assert hasattr(main, "__call__")

        # Verify it's an async function
        import inspect

        assert inspect.iscoroutinefunction(main)


class TestWsSbConfiguration:
    """Test cases for ws_sb configuration handling."""

    def test_config_file_structure(self):
        """Test that the configuration file has the expected structure."""
        config_path = Path("conf/ws.json")

        # Skip if config file doesn't exist
        if not config_path.exists():
            pytest.skip("Configuration file not found")

        with open(config_path, "r") as f:
            config = json.load(f)

        # Verify required keys exist
        assert "server_url" in config
        assert "device_name" in config
        assert "token" in config
        assert "tables" in config

        # Verify server_url is a valid WebSocket URL
        assert config["server_url"].startswith(("ws://", "wss://"))

        # Verify tables is a list
        assert isinstance(config["tables"], list)

        # Verify at least one table exists
        assert len(config["tables"]) > 0

        # Verify table structure
        for table in config["tables"]:
            assert "table_id" in table
            assert "name" in table

    def test_ws_sb_module_import(self):
        """Test that ws_sb module can be imported successfully."""
        try:
            from studio_api import ws_sb

            assert hasattr(ws_sb, "test_sbo_001_device_info")
            assert hasattr(ws_sb, "main")
        except ImportError as e:
            pytest.fail(f"Failed to import ws_sb module: {e}")

    def test_ws_client_dependencies(self):
        """Test that required ws_client dependencies are available."""
        try:
            from studio_api.ws_client import (
                SmartStudioWebSocketClient,
                StudioServiceStatusEnum,
                StudioMaintenanceStatusEnum,
            )

            # Test that classes exist
            assert SmartStudioWebSocketClient is not None
            assert StudioServiceStatusEnum is not None
            assert StudioMaintenanceStatusEnum is not None

            # Test that required methods exist
            assert hasattr(StudioServiceStatusEnum, "get_random_status")
            assert hasattr(StudioMaintenanceStatusEnum, "get_random_status")

        except ImportError as e:
            pytest.fail(f"Failed to import ws_client dependencies: {e}")


@pytest.mark.integration
class TestWsSbIntegration:
    """Integration tests for ws_sb module (marked as slow)."""

    @pytest.mark.asyncio
    async def test_full_workflow_integration(self):
        """Test the complete workflow with mocked dependencies."""
        # This test would run the full workflow with mocked WebSocket server
        # Marked as integration test since it tests the complete flow
        pytest.skip("Integration test - requires WebSocket server")


if __name__ == "__main__":
    pytest.main([__file__])
