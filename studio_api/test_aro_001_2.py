#!/usr/bin/env python3
"""
Mock ARO-001-2 WebSocket client for testing error signal handling.
This client stays in idle state and listens for error signals from the server.
When it receives an error signal from ARO-001-1, it transitions from idle to running state.
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

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


class DeviceState(Enum):
    """Device state enumeration."""

    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class ARO001_2MockClient:
    """Mock ARO-001-2 WebSocket client that listens for error signals."""

    def __init__(
        self, server_url: str, table_id: str, device_name: str, token: str
    ):
        self.server_url = server_url
        self.table_id = table_id
        self.device_name = device_name
        self.token = token
        self.websocket = None
        self.current_state = DeviceState.IDLE
        self.running = False
        self.error_signal_received = False

    async def connect(self):
        """Connect to the WebSocket server."""
        try:
            import websockets

            # Create connection URL for ARO-001-2 device
            # Use the same format as ws_client.py: ?token=TOKEN&id=TABLE_ID&device=DEVICE_NAME
            connection_url = f"{self.server_url}?token={self.token}&id={self.table_id}&device={self.device_name}"

            logger.info(f"🔗 Connecting ARO-001-2 to {connection_url}")
            self.websocket = await websockets.connect(connection_url)
            logger.info("✅ ARO-001-2 WebSocket connection established")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect ARO-001-2: {e}")
            return False

    async def send_idle_status(self):
        """Send idle status update to the server."""
        if not self.websocket:
            logger.error("Not connected to server")
            return False

        try:
            # Send idle status with device information
            status_data = {
                "device": "ARO-001-2",
                "status": "idle",
                "timestamp": datetime.now().isoformat(),
                "state": self.current_state.value,
                "message": "Device is in idle state, waiting for error signals",
            }

            message = json.dumps(status_data)
            await self.websocket.send(message)
            logger.info(f"📤 ARO-001-2 sent idle status: {status_data}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send idle status: {e}")
            return False

    async def send_running_status(self):
        """Send running status update to the server."""
        if not self.websocket:
            logger.error("Not connected to server")
            return False

        try:
            # Send running status with device information
            status_data = {
                "device": "ARO-001-2",
                "status": "running",
                "timestamp": datetime.now().isoformat(),
                "state": self.current_state.value,
                "message": "Device is now running after receiving error signal",
            }

            message = json.dumps(status_data)
            await self.websocket.send(message)
            logger.info(f"📤 ARO-001-2 sent running status: {status_data}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send running status: {e}")
            return False

    async def handle_error_signal(self, error_data: Dict[str, Any]):
        """Handle incoming error signal from the server."""
        try:
            logger.info(f"🚨 ARO-001-2 received error signal: {error_data}")

            # Check if the error signal is from ARO-001-1
            if "data" in error_data and "signal" in error_data["data"]:
                signal = error_data["data"]["signal"]
                logger.info(f"📋 Error signal details: {signal}")

                # Transition from idle to running state
                if self.current_state == DeviceState.IDLE:
                    logger.info(
                        "🔄 ARO-001-2 transitioning from IDLE to RUNNING state"
                    )
                    self.current_state = DeviceState.RUNNING
                    self.error_signal_received = True

                    # Send running status update
                    await self.send_running_status()

                    # Send acknowledgment back to server
                    ack_data = {
                        "device": "ARO-001-2",
                        "action": "error_signal_acknowledged",
                        "timestamp": datetime.now().isoformat(),
                        "original_signal": signal,
                        "new_state": self.current_state.value,
                    }

                    ack_message = json.dumps(ack_data)
                    await self.websocket.send(ack_message)
                    logger.info(
                        f"📤 ARO-001-2 sent acknowledgment: {ack_data}"
                    )

                    return True
                else:
                    logger.warning(
                        f"⚠️ ARO-001-2 received error signal but is not in IDLE state (current: {self.current_state.value})"
                    )
                    return False
            else:
                logger.warning("⚠️ ARO-001-2 received malformed error signal")
                return False

        except Exception as e:
            logger.error(f"❌ Error handling error signal: {e}")
            return False

    async def listen_for_messages(self):
        """Listen for incoming messages from the server."""
        try:
            while self.running and self.websocket:
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(
                        self.websocket.recv(), timeout=1.0
                    )

                    if message:
                        try:
                            # Parse JSON message
                            data = json.loads(message)
                            logger.info(
                                f"📨 ARO-001-2 received message: {data}"
                            )

                            # Check if it's an error signal
                            if (
                                isinstance(data, dict)
                                and data.get("event") == "exception"
                            ):
                                await self.handle_error_signal(data)
                            else:
                                logger.info(
                                    f"📝 ARO-001-2 received other message: {data}"
                                )

                        except json.JSONDecodeError:
                            logger.info(
                                f"📝 ARO-001-2 received non-JSON message: {message}"
                            )

                except asyncio.TimeoutError:
                    # Timeout is expected, continue listening
                    continue
                except Exception as e:
                    if "ConnectionClosed" in str(type(e)):
                        logger.warning(
                            "🔌 ARO-001-2 WebSocket connection closed"
                        )
                        break

        except Exception as e:
            logger.error(f"❌ Error in message listener: {e}")

    async def idle_loop(self):
        """Main idle loop that sends periodic status updates."""
        try:
            logger.info("🔄 ARO-001-2 starting idle loop")

            while self.running and not self.error_signal_received:
                # Send idle status every 5 seconds
                await self.send_idle_status()

                # Wait for 5 seconds or until error signal received
                for _ in range(50):  # 5 seconds = 50 * 0.1 second intervals
                    if self.error_signal_received:
                        break
                    await asyncio.sleep(0.1)

            if self.error_signal_received:
                logger.info(
                    "🎯 ARO-001-2 error signal received, transitioning to running state"
                )
                # Keep running for a while to show the running state
                for _ in range(30):  # Run for 3 seconds
                    await self.send_running_status()
                    await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"❌ Error in idle loop: {e}")

    async def start(self):
        """Start the ARO-001-2 mock client."""
        try:
            # Connect to server
            if not await self.connect():
                return False

            self.running = True
            logger.info("🚀 ARO-001-2 mock client started")

            # Start message listener and idle loop concurrently
            await asyncio.gather(self.listen_for_messages(), self.idle_loop())

            return True

        except Exception as e:
            logger.error(f"❌ Error starting ARO-001-2 mock client: {e}")
            return False

    async def stop(self):
        """Stop the ARO-001-2 mock client."""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            logger.info("🛑 ARO-001-2 mock client stopped")

    async def disconnect(self):
        """Disconnect from the server."""
        await self.stop()


async def main():
    """Main function for ARO-001-2 mock client."""

    # Load configuration from ws.json
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "conf", "ws.json"
    )

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        SERVER_URL = config["server_url"]
        DEVICE_NAME = "ARO-001-2"  # Override device name for ARO-001-2
        TOKEN = config["token"]
        TABLE_ID = "ARO-001"

        logger.info(f"📋 Loaded configuration from {config_path}")
        logger.info(f"   - Server: {SERVER_URL}")
        logger.info(f"   - Device: {DEVICE_NAME}")
        logger.info(f"   - Table: {TABLE_ID}")

    except FileNotFoundError:
        logger.error(f"❌ Configuration file not found: {config_path}")
        return
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in configuration file: {e}")
        return
    except KeyError as e:
        logger.error(f"❌ Missing required configuration key: {e}")
        return

    # Create ARO-001-2 mock client
    client = ARO001_2MockClient(SERVER_URL, TABLE_ID, DEVICE_NAME, TOKEN)

    try:
        logger.info("🎰 ARO-001-2 Mock Client - Error Signal Listener")
        logger.info("=" * 60)
        logger.info("📋 This client will:")
        logger.info("   1. Connect as ARO-001-2 device")
        logger.info(
            "   2. Stay in IDLE state and send periodic status updates"
        )
        logger.info("   3. Listen for error signals from the server")
        logger.info(
            "   4. Transition to RUNNING state when error signal received"
        )
        logger.info("=" * 60)

        # Start the mock client
        await client.start()

    except KeyboardInterrupt:
        logger.info("\n🛑 ARO-001-2 mock client interrupted by user")
    except Exception as e:
        logger.error(f"❌ Error in ARO-001-2 mock client: {e}")
    finally:
        # Clean up
        await client.disconnect()
        logger.info("✅ ARO-001-2 mock client cleanup completed")


if __name__ == "__main__":
    asyncio.run(main())
