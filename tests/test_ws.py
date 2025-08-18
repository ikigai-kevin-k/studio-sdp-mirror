"""
Simplified unit tests for WebSocket server functionality.

This module contains tests for the simplified StudioWebSocketServer class,
focusing only on receiving table/device status updates from clients.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from .mock_ws_server import (
    StudioWebSocketServer,
    StudioServiceStatusEnum,
    StudioDeviceStatusEnum,
    StudioStatus,
)


class TestStudioServiceStatusEnum:
    """Test cases for StudioServiceStatusEnum."""

    def test_enum_values(self):
        """Test that enum values are correctly defined."""
        assert StudioServiceStatusEnum.UP == "up"
        assert StudioServiceStatusEnum.DOWN == "down"
        assert StudioServiceStatusEnum.STANDBY == "standby"
        assert StudioServiceStatusEnum.CALIBRATION == "calibration"
        assert StudioServiceStatusEnum.EXCEPTION == "exception"


class TestStudioDeviceStatusEnum:
    """Test cases for StudioDeviceStatusEnum."""

    def test_enum_values(self):
        """Test that enum values are correctly defined."""
        assert StudioDeviceStatusEnum.UP == "up"
        assert StudioDeviceStatusEnum.DOWN == "down"


class TestStudioStatus:
    """Test cases for StudioStatus dataclass."""

    def test_studio_status_creation(self):
        """Test creating a StudioStatus instance."""
        timestamp = datetime.now()
        status = StudioStatus(
            TABLE_ID="ARO-001",
            UPTIME=100,
            TIMESTAMP=timestamp,
            MAINTENANCE=False,
            SDP=StudioServiceStatusEnum.UP,
            IDP=StudioServiceStatusEnum.STANDBY,
            BROKER=StudioDeviceStatusEnum.UP,
            ZCam=StudioDeviceStatusEnum.DOWN,
            ROULETTE=StudioDeviceStatusEnum.UP,
            SHAKER=StudioDeviceStatusEnum.DOWN,
            BARCODE_SCANNER=StudioDeviceStatusEnum.UP,
            NFC_SCANNER=StudioDeviceStatusEnum.DOWN,
        )

        assert status.TABLE_ID == "ARO-001"
        assert status.UPTIME == 100
        assert status.TIMESTAMP == timestamp
        assert status.MAINTENANCE is False
        assert status.SDP == StudioServiceStatusEnum.UP
        assert status.IDP == StudioServiceStatusEnum.STANDBY
        assert status.BROKER == StudioDeviceStatusEnum.UP
        assert status.ZCam == StudioDeviceStatusEnum.DOWN
        assert status.ROULETTE == StudioServiceStatusEnum.UP
        assert status.SHAKER == StudioDeviceStatusEnum.DOWN
        assert status.BARCODE_SCANNER == StudioDeviceStatusEnum.UP
        assert status.NFC_SCANNER == StudioDeviceStatusEnum.DOWN

    def test_to_dict_method(self):
        """Test the to_dict method converts correctly."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        status = StudioStatus(
            TABLE_ID="ARO-001",
            UPTIME=100,
            TIMESTAMP=timestamp,
            MAINTENANCE=False,
            SDP=StudioServiceStatusEnum.UP,
            IDP=StudioServiceStatusEnum.STANDBY,
            BROKER=StudioDeviceStatusEnum.UP,
            ZCam=StudioDeviceStatusEnum.DOWN,
            ROULETTE=StudioDeviceStatusEnum.UP,
            SHAKER=StudioDeviceStatusEnum.DOWN,
            BARCODE_SCANNER=StudioDeviceStatusEnum.UP,
            NFC_SCANNER=StudioDeviceStatusEnum.DOWN,
        )

        result = status.to_dict()

        assert isinstance(result, dict)
        assert result["TABLE_ID"] == "ARO-001"
        assert result["UPTIME"] == 100
        assert result["TIMESTAMP"] == "2024-01-01T12:00:00"
        assert result["MAINTENANCE"] is False
        assert result["SDP"] == StudioServiceStatusEnum.UP
        assert result["IDP"] == StudioServiceStatusEnum.STANDBY


class TestStudioWebSocketServer:
    """Test cases for simplified StudioWebSocketServer class."""

    @pytest.fixture
    def server(self):
        """Create a server instance for testing."""
        return StudioWebSocketServer(host="localhost", port=8080)

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket connection."""
        websocket = AsyncMock()
        websocket.send = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    def test_server_initialization(self, server):
        """Test server initialization with correct parameters."""
        assert server.host == "localhost"
        assert server.port == 8080
        assert len(server.studio_status) == 0

    def test_parse_query_params_valid(self, server):
        """Test parsing valid query parameters."""
        path = "/?id=ARO-001_dealerPC&token=MY_TOKEN"
        params = server._parse_query_params(path)

        assert params["id"] == "ARO-001_dealerPC"
        assert params["token"] == "MY_TOKEN"

    def test_parse_query_params_empty(self, server):
        """Test parsing empty query parameters."""
        path = "/"
        params = server._parse_query_params(path)

        assert params == {}

    def test_parse_query_params_malformed(self, server):
        """Test parsing malformed query parameters."""
        path = "/?id=ARO-001_dealerPC&token"
        params = server._parse_query_params(path)

        assert params["id"] == "ARO-001_dealerPC"
        assert "token" not in params

    @pytest.mark.asyncio
    async def test_handle_connection_missing_auth(
        self, server, mock_websocket
    ):
        """Test connection handling with missing authentication."""

        # Mock recv to return invalid auth data
        mock_websocket.recv = AsyncMock(
            return_value=json.dumps({"id": "", "token": ""})
        )

        await server.handle_connection(mock_websocket)

        mock_websocket.close.assert_called_once_with(
            1008, "Missing authentication parameters"
        )

    @pytest.mark.asyncio
    async def test_handle_connection_valid_auth(self, server, mock_websocket):
        """Test connection handling with valid authentication."""

        # Mock recv to return valid auth data
        mock_websocket.recv = AsyncMock(
            return_value=json.dumps(
                {"id": "ARO-001_dealerPC", "token": "MY_TOKEN"}
            )
        )

        # Mock the message loop to avoid infinite loop
        class MockAsyncIterator:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise StopAsyncIteration

        mock_websocket.__aiter__ = MagicMock(return_value=MockAsyncIterator())

        await server.handle_connection(mock_websocket)

        # Check that status was initialized
        assert "ARO-001" in server.studio_status

        # Check that messages were sent (welcome + initial status)
        assert mock_websocket.send.call_count == 2

        # Check initial status message (second call)
        sent_data = json.loads(mock_websocket.send.call_args_list[1][0][0])
        assert sent_data["TABLE_ID"] == "ARO-001"
        assert sent_data["SDP"] == StudioServiceStatusEnum.STANDBY
        assert sent_data["IDP"] == StudioServiceStatusEnum.STANDBY

    @pytest.mark.asyncio
    async def test_handle_status_update_service_status(
        self, server, mock_websocket
    ):
        """Test handling service status update message."""
        # Setup initial status
        table_id = "ARO-001"
        server.studio_status[table_id] = StudioStatus(
            TABLE_ID=table_id,
            UPTIME=0,
            TIMESTAMP=datetime.now(),
            MAINTENANCE=False,
            SDP=StudioServiceStatusEnum.STANDBY,
            IDP=StudioServiceStatusEnum.STANDBY,
            BROKER=StudioDeviceStatusEnum.DOWN,
            ZCam=StudioDeviceStatusEnum.DOWN,
            ROULETTE=StudioDeviceStatusEnum.DOWN,
            SHAKER=StudioDeviceStatusEnum.DOWN,
            BARCODE_SCANNER=StudioDeviceStatusEnum.DOWN,
            NFC_SCANNER=StudioDeviceStatusEnum.DOWN,
        )

        message = json.dumps({"sdp": StudioServiceStatusEnum.UP})

        await server._handle_status_update(mock_websocket, table_id, message)

        # Check that status was updated
        assert server.studio_status[table_id].SDP == StudioServiceStatusEnum.UP

        # Check that confirmation was sent
        mock_websocket.send.assert_called_once()
        response = json.loads(mock_websocket.send.call_args[0][0])
        assert response["status"] == "updated"
        assert response["table_id"] == table_id

    @pytest.mark.asyncio
    async def test_handle_status_update_device_status(
        self, server, mock_websocket
    ):
        """Test handling device status update message."""
        # Setup initial status
        table_id = "ARO-001"
        server.studio_status[table_id] = StudioStatus(
            TABLE_ID=table_id,
            UPTIME=0,
            TIMESTAMP=datetime.now(),
            MAINTENANCE=False,
            SDP=StudioServiceStatusEnum.STANDBY,
            IDP=StudioServiceStatusEnum.STANDBY,
            BROKER=StudioDeviceStatusEnum.DOWN,
            ZCam=StudioDeviceStatusEnum.DOWN,
            ROULETTE=StudioDeviceStatusEnum.DOWN,
            SHAKER=StudioDeviceStatusEnum.DOWN,
            BARCODE_SCANNER=StudioDeviceStatusEnum.DOWN,
            NFC_SCANNER=StudioDeviceStatusEnum.DOWN,
        )

        message = json.dumps(
            {
                "roulette": StudioDeviceStatusEnum.UP,
                "shaker": StudioDeviceStatusEnum.UP,
            }
        )

        await server._handle_status_update(mock_websocket, table_id, message)

        # Check that status was updated
        assert (
            server.studio_status[table_id].ROULETTE
            == StudioDeviceStatusEnum.UP
        )
        assert (
            server.studio_status[table_id].SHAKER == StudioDeviceStatusEnum.UP
        )

        # Check that uptime was incremented
        assert server.studio_status[table_id].UPTIME == 1

    @pytest.mark.asyncio
    async def test_handle_status_update_invalid_json(
        self, server, mock_websocket
    ):
        """Test handling invalid JSON message."""
        table_id = "ARO-001"
        message = "invalid json message"

        await server._handle_status_update(mock_websocket, table_id, message)

        # Check that error response was sent
        mock_websocket.send.assert_called_once()
        response = json.loads(mock_websocket.send.call_args[0][0])
        assert response["error"] == "Invalid JSON format"


@pytest.mark.asyncio
class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""

    async def test_full_connection_flow(self):
        """Test complete connection flow from connection to status updates."""
        server = StudioWebSocketServer()

        # Mock WebSocket connection
        websocket = AsyncMock()
        websocket.send = AsyncMock()
        websocket.close = AsyncMock()

        # Mock the message loop with proper async iterator
        messages = [
            json.dumps({"sdp": StudioServiceStatusEnum.UP}),
            json.dumps({"roulette": StudioDeviceStatusEnum.UP}),
        ]

        class MockAsyncIterator:
            def __init__(self, msgs):
                self.messages = msgs.copy()

            def __aiter__(self):
                return self

            async def __anext__(self):
                if not self.messages:
                    raise StopAsyncIteration
                return self.messages.pop(0)

        mock_iterator = MockAsyncIterator(messages)
        websocket.__aiter__ = MagicMock(return_value=mock_iterator)

        # Simulate connection
        # Mock recv to return valid auth data
        websocket.recv = AsyncMock(
            return_value=json.dumps(
                {"id": "ARO-001_dealerPC", "token": "MY_TOKEN"}
            )
        )

        await server.handle_connection(websocket)

        # Verify status was initialized
        assert "ARO-001" in server.studio_status

        # Verify status updates were processed
        status = server.studio_status["ARO-001"]
        assert status.SDP == StudioServiceStatusEnum.UP
        assert status.ROULETTE == StudioDeviceStatusEnum.UP
        assert status.UPTIME == 2  # Two messages processed

        # Verify responses were sent
        assert (
            websocket.send.call_count >= 3
        )  # Initial status + 2 confirmations


if __name__ == "__main__":
    pytest.main([__file__])
