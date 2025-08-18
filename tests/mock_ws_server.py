"""
Simplified WebSocket server for receiving table/device status updates.

This module provides a minimal WebSocket server that only handles
incoming status updates from clients.
"""

import asyncio
import json
import logging
from typing import Dict
from dataclasses import dataclass, asdict
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StudioServiceStatusEnum:
    """Enumeration for Studio service status."""

    UP = "up"
    DOWN = "down"
    STANDBY = "standby"
    CALIBRATION = "calibration"
    EXCEPTION = "exception"


class StudioDeviceStatusEnum:
    """Enumeration for Studio device status."""

    UP = "up"
    DOWN = "down"


@dataclass
class StudioStatus:
    """Data class for Studio status information."""

    TABLE_ID: str
    UPTIME: int
    TIMESTAMP: datetime
    MAINTENANCE: bool
    SDP: str
    IDP: str
    BROKER: str
    ZCam: str
    ROULETTE: str
    SHAKER: str
    BARCODE_SCANNER: str
    NFC_SCANNER: str

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["TIMESTAMP"] = self.TIMESTAMP.isoformat()
        return data


class StudioWebSocketServer:
    """Simplified WebSocket server for receiving table/device status updates."""

    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.studio_status: Dict[str, StudioStatus] = {}

    async def handle_connection(self, websocket: WebSocketServerProtocol):
        """Handle new WebSocket connection."""
        try:
            # Get the path from the websocket request
            # For websockets library, we need to get the path differently
            path = str(websocket.remote_address)

            # Since we can't get the query parameters from the websocket object directly,
            # we'll use a simple approach and assume the client sends the table_id and token
            # in the first message instead of query parameters

            # Send welcome message
            welcome_msg = {
                "message": "Connected to Studio WebSocket Server",
                "status": "ready",
            }
            await websocket.send(json.dumps(welcome_msg))

            # Wait for authentication message
            auth_message = await websocket.recv()
            auth_data = json.loads(auth_message)

            user_id = auth_data.get("id")
            token = auth_data.get("token")

            if not user_id or not token:
                logger.error("Missing user ID or token in authentication message")
                await websocket.close(1008, "Missing authentication parameters")
                return

            # Extract table ID from user ID (format: TABLE_ID_DEVICE_NAME_...)
            table_id = user_id.split("_")[0] if "_" in user_id else user_id

            logger.info(f"New connection from {user_id} for table {table_id}")

            # Initialize studio status for this table if not exists
            if table_id not in self.studio_status:
                self.studio_status[table_id] = StudioStatus(
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

            # Send current status to new client
            current_status = self.studio_status[table_id].to_dict()
            await websocket.send(json.dumps(current_status))

            # Handle incoming status update messages
            async for message in websocket:
                await self._handle_status_update(websocket, table_id, message)

        except websockets.exceptions.ConnectionClosed:
            logger.info(
                f"Connection closed for {user_id if 'user_id' in locals() else 'unknown'}"
            )
        except Exception as e:
            logger.error(f"Error handling connection: {e}")

    def _parse_query_params(self, path: str) -> Dict[str, str]:
        """Parse query parameters from WebSocket path."""
        params = {}
        if "?" in path:
            query_string = path.split("?")[1]
            for param in query_string.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[key] = value
        return params

    async def _handle_status_update(
        self, websocket: WebSocketServerProtocol, table_id: str, message: str
    ):
        """Handle incoming status update message."""
        try:
            data = json.loads(message)
            logger.info(f"Received status update from {table_id}: {data}")

            # Update studio status based on received data
            if table_id in self.studio_status:
                status = self.studio_status[table_id]

                # Update service status
                if "sdp" in data:
                    status.SDP = data["sdp"]
                if "idp" in data:
                    status.IDP = data["idp"]

                # Update device status
                if "broker" in data:
                    status.BROKER = data["broker"]
                if "zcam" in data:
                    status.ZCam = data["zcam"]
                if "roulette" in data:
                    status.ROULETTE = data["roulette"]
                if "shaker" in data:
                    status.SHAKER = data["shaker"]
                if "barcode_scanner" in data:
                    status.BARCODE_SCANNER = data["barcode_scanner"]
                if "nfc_scanner" in data:
                    status.NFC_SCANNER = data["nfc_scanner"]

                # Update timestamp and uptime
                status.TIMESTAMP = datetime.now()
                status.UPTIME += 1

                # Send confirmation to sender
                response = {"status": "updated", "table_id": table_id}
                await websocket.send(json.dumps(response))

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON message from {table_id}: {message}")
            await websocket.send(json.dumps({"error": "Invalid JSON format"}))
        except Exception as e:
            logger.error(f"Error handling message from {table_id}: {e}")
            await websocket.send(json.dumps({"error": str(e)}))

    async def start(self):
        """Start the WebSocket server."""
        logger.info(f"Starting WebSocket server on ws://{self.host}:{self.port}")

        async with websockets.serve(self.handle_connection, self.host, self.port):
            logger.info("WebSocket server started successfully")
            await asyncio.Future()  # Run forever


async def main():
    """Main function to run the WebSocket server."""
    server = StudioWebSocketServer()
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
