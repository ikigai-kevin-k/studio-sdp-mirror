#!/usr/bin/env python3
"""
Test script for sending error signals to Roulette Game (ARO-001 table).
Based on new WebSocket server API with error signal support.
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

# Add the current directory to Python path to import ws_client
sys.path.append(os.path.dirname(__file__))

from ws_client import (
    SmartStudioWebSocketClient,
    StudioServiceStatusEnum,
    StudioMaintenanceStatusEnum,
)

# Configure logging with timestamp format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# Global variable to store the WebSocket client instance
_ws_client = None
_table_id = None


class ErrorSignalClient:
    """Enhanced WebSocket client for sending error signals."""

    def __init__(
        self, server_url: str, table_id: str, device_name: str, token: str
    ):
        self.server_url = server_url
        self.table_id = table_id
        self.device_name = device_name
        self.token = token
        self.websocket = None

    async def connect(self):
        """Connect to the WebSocket server with correct API parameters."""
        try:
            import websockets

            # Create connection URL according to spec: ?id=ARO-001_dealerPC&token=MY_TOKEN
            connection_url = f"{self.server_url}?id={self.table_id}_{self.device_name}&token={self.token}"

            logger.info(f"Connecting to {connection_url}")
            self.websocket = await websockets.connect(connection_url)
            logger.info("✅ WebSocket connection established")
            return True

        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    async def send_error_signal(
        self, signal_data: Dict[str, Any], cmd_data: Dict[str, Any] = None
    ):
        """Send error signal to the server."""
        if not self.websocket:
            logger.error("Not connected to server")
            return False

        try:
            # Create error signal message according to spec:
            # { event: 'exception', data: { signal: Signal, cmd: any } }
            msg = {
                "event": "exception",
                "data": {
                    "signal": signal_data,  # Wrap signal_data in signal object as per spec
                    "cmd": cmd_data or {},  # Include cmd field as per spec
                },
            }

            # Send the error signal
            message = json.dumps(msg)
            await self.websocket.send(message)
            logger.info(f"📤 Sent error signal: {msg}")

            # Wait for response
            try:
                response = await asyncio.wait_for(
                    self.websocket.recv(), timeout=5.0
                )
                logger.info(f"📨 Server response: {response}")
            except asyncio.TimeoutError:
                logger.warning("⏰ No response received for error signal")

            return True

        except Exception as e:
            logger.error(f"Failed to send error signal: {e}")
            return False

    async def send_status_update(self, status_data: Dict[str, Any]):
        """Send status update to the server."""
        if not self.websocket:
            logger.error("Not connected to server")
            return False

        try:
            # Send status update directly (no event wrapper needed for status)
            message = json.dumps(status_data)
            await self.websocket.send(message)
            logger.info(f"📤 Sent status update: {status_data}")

            # Wait for response
            try:
                response = await asyncio.wait_for(
                    self.websocket.recv(), timeout=5.0
                )
                logger.info(f"📨 Server response: {response}")
            except asyncio.TimeoutError:
                logger.warning("⏰ No response received for status update")

            return True

        except Exception as e:
            logger.error(f"Failed to send status update: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the server."""
        if self.websocket:
            await self.websocket.close()
            logger.info("Disconnected from server")


async def send_roulette_sensor_stuck_error(
    table_id: str = "ARO-001-1", device_id: str = "ARO-001-1"
) -> bool:
    """
    Send roulette sensor stuck error signal for ARO-001 table.

    Args:
        table_id: Table ID for the Roulette game (default: ARO-001)
        device_id: Device ID for the connection (default: ARO-001-1)

    Returns:
        bool: True if error signal sent successfully, False otherwise
    """

    # Load configuration from ws.json
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "conf", "ws.json"
    )
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        SERVER_URL = config["server_url"]
        DEVICE_NAME = config["device_name"]
        TOKEN = config["token"]

        logger.info(f"📋 Loaded configuration from {config_path}")
        logger.info(f"   - Server: {SERVER_URL}")
        logger.info(f"   - Device: {DEVICE_NAME}")
        logger.info(f"   - Table: {table_id}")

    except FileNotFoundError:
        logger.error(f"❌ Configuration file not found: {config_path}")
        return False
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in configuration file: {e}")
        return False
    except KeyError as e:
        logger.error(f"❌ Missing required configuration key: {e}")
        return False

    # Create error signal client
    client = ErrorSignalClient(SERVER_URL, table_id, DEVICE_NAME, TOKEN)

    try:
        # Connect to the table
        logger.info(f"🔗 Connecting to {table_id}...")
        if not await client.connect():
            logger.error(f"❌ Failed to connect to {table_id}")
            return False

        logger.info(f"✅ Successfully connected to {table_id}")

        # Create roulette sensor stuck error signal according to spec
        signal_data = {
            "msgId": str(uuid.uuid4()),
            "metadata": {
                "title": "SENSOR STUCK",
                "description": "Sensor broken causes roulette machine idle",
                "code": "ARE.3",
                "suggestion": "Clean or replace the ball",
            },
        }

        # Send the error signal
        logger.info(
            f"📤 Sending roulette sensor stuck error signal to {table_id}..."
        )
        logger.info(f"   - Signal: {signal_data}")

        success = await client.send_error_signal(signal_data)

        if success:
            logger.info(
                "🎯 Roulette sensor stuck error signal sent successfully!"
            )
        else:
            logger.error(
                "❌ Failed to send roulette sensor stuck error signal"
            )

        return success

    except Exception as e:
        logger.error(f"❌ Error during error signal sending: {e}")
        return False

    finally:
        # Disconnect from server
        try:
            await client.disconnect()
            logger.info(f"✅ Disconnected from {table_id}")
        except Exception as e:
            logger.error(f"❌ Error disconnecting from {table_id}: {e}")


async def main():
    """Main function for testing error signal functionality."""

    logger.info("🎰 Roulette Game Error Signal Test")
    logger.info("=" * 50)

    # Test 1: Send single roulette sensor stuck error
    logger.info("\n📤 Test: Sending roulette sensor stuck error signal...")
    success1 = await send_roulette_sensor_stuck_error()

    if success1:
        logger.info("✅ Single error signal test completed successfully")
    else:
        logger.error("❌ Single error signal test failed")


if __name__ == "__main__":
    asyncio.run(main())
