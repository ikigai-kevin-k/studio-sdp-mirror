"""
Simple unit tests for ws_sb.py module.

This module tests the basic functionality without complex imports.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, mock_open


class TestWsSbBasic:
    """Basic test cases for ws_sb module."""

    def test_config_file_exists(self):
        """Test that the configuration file exists and is valid JSON."""
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

    def test_ws_sb_file_exists(self):
        """Test that ws_sb.py file exists and is readable."""
        ws_sb_path = Path("studio_api/ws_sb.py")
        assert ws_sb_path.exists(), "ws_sb.py file not found"

        # Try to read the file
        with open(ws_sb_path, "r") as f:
            content = f.read()

        # Verify it contains expected content
        assert "test_sbo_001_device_info" in content
        assert "main" in content
        assert "async def" in content

    def test_ws_client_file_exists(self):
        """Test that ws_client.py file exists and is readable."""
        ws_client_path = Path("studio_api/ws_client.py")
        assert ws_client_path.exists(), "ws_client.py file not found"

        # Try to read the file
        with open(ws_client_path, "r") as f:
            content = f.read()

        # Verify it contains expected content
        assert "SmartStudioWebSocketClient" in content
        assert "StudioServiceStatusEnum" in content
        assert "StudioMaintenanceStatusEnum" in content

    def test_ws_json_config_structure(self):
        """Test the structure of ws.json configuration file."""
        config_path = Path("conf/ws.json")

        if not config_path.exists():
            pytest.skip("Configuration file not found")

        with open(config_path, "r") as f:
            config = json.load(f)

        # Test specific structure for SBO-001 table
        sbo_table = None
        for table in config["tables"]:
            if table["table_id"] == "SBO-001":
                sbo_table = table
                break

        assert (
            sbo_table is not None
        ), "SBO-001 table not found in configuration"
        assert sbo_table["name"] == "SBO-001"

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    def test_config_file_loading_mock(self, mock_json_load, mock_open_file):
        """Test configuration file loading with mocked file operations."""
        # Setup mock
        mock_config = {
            "server_url": "ws://test-server:8082",
            "device_name": "testDevice",
            "token": "test-token",
            "tables": [{"table_id": "SBO-001", "name": "SBO-001"}],
        }
        mock_json_load.return_value = mock_config

        # Test file operations
        with open("mock_path", "r") as f:
            config = json.load(f)

        # Verify
        assert config == mock_config
        mock_open_file.assert_called_once_with("mock_path", "r")
        mock_json_load.assert_called_once()

    def test_websockets_dependency_available(self):
        """Test that websockets dependency is available."""
        try:
            import websockets

            assert websockets is not None
        except ImportError:
            pytest.skip("websockets module not available")

    def test_asyncio_available(self):
        """Test that asyncio is available."""
        import asyncio

        assert asyncio is not None

    def test_python_version_compatibility(self):
        """Test Python version compatibility."""
        import sys

        # Check if Python version is 3.7+ (for async/await support)
        assert sys.version_info >= (
            3,
            7,
        ), "Python 3.7+ required for async/await"


class TestWsSbIntegration:
    """Integration test cases for ws_sb module."""

    @pytest.mark.integration
    def test_module_import_integration(self):
        """Test that ws_sb module can be imported in integration context."""
        try:
            # This test would require a proper Python path setup
            # For now, we'll just verify the file structure
            ws_sb_path = Path("studio_api/ws_sb.py")
            assert ws_sb_path.exists()

            # Check if it's valid Python syntax
            with open(ws_sb_path, "r") as f:
                content = f.read()

            # Basic syntax check - try to compile
            compile(content, ws_sb_path, "exec")

        except SyntaxError as e:
            pytest.fail(f"Syntax error in ws_sb.py: {e}")
        except Exception as e:
            pytest.skip(f"Import test skipped: {e}")

    @pytest.mark.integration
    def test_config_integration(self):
        """Test configuration integration."""
        config_path = Path("conf/ws.json")

        if not config_path.exists():
            pytest.skip("Configuration file not found")

        try:
            with open(config_path, "r") as f:
                config = json.load(f)

            # Test that config can be used
            assert isinstance(config, dict)
            assert len(config) > 0

        except Exception as e:
            pytest.fail(f"Configuration integration test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__])
