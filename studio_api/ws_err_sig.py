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
from enum import Enum

# Add the current directory to Python path to import ws_client
sys.path.append(os.path.dirname(__file__))

from ws_client import (
    SmartStudioWebSocketClient,
    StudioServiceStatusEnum,
    StudioMaintenanceStatusEnum,
)


class ErrorMsgId(Enum):
    """Error message ID constants for exception signals."""

    # Roulette errors
    ROULETTE_NO_BALL_DETECT = "ROULETTE_NO_BALL_DETECT"
    ROULETTE_NO_WIN_NUM = "ROULETTE_NO_WIN_NUM"
    ROULETTE_NO_REACH_POS = "ROULETTE_NO_REACH_POS"
    ROULETTE_INVALID_AFTER_RELAUNCH = "ROULETTE_INVALID_AFTER_RELAUNCH"
    ROULETTE_SENSOR_STUCK = "ROULETTE_SENSOR_STUCK"
    ROUELTTE_WRONG_BALL_DIR = "ROUELTTE_WRONG_BALL_DIR"
    ROULETTE_WRONG_WHEEL_DIR = "ROULETTE_WRONG_WHEEL_DIR"
    ROULETTE_LAUNCH_FAIL = "ROULETTE_LAUNCH_FAIL"
    ROULETTE_ENCODER_FAIL = "ROULETTE_ENCODER_FAIL"
    ROULETTE_BALL_DROP_FAIL = "ROULETTE_BALL_DROP_FAIL"
    ROULETTE_COMPRESSOR_LEAK = "ROULETTE_COMPRESSOR_LEAK"
    ROULETTE_STUCK_NMB = "ROULETTE_STUCK_NMB"

    # Sicbo errors
    SICBO_INVALID_RESULT = "SICBO_INVALID_RESULT"
    SICBO_NO_SHAKE = "SICBO_NO_SHAKE"
    SICBO_INVALID_AFTER_RESHAKE = "SICBO_INVALID_AFTER_RESHAKE"

    # Baccarat errors
    BACCARAT_INVALID_RESULT = "BACCARAT_INVALID_RESULT"
    BACCARAT_WRONG_CARD_DEAL_POS = "BACCARAT_WRONG_CARD_DEAL_POS"
    BACCARAT_INVALID_AFTER_REDEAL = "BACCARAT_INVALID_AFTER_REDEAL"
    BACCARAT_DEAL_EXTRA_CARD = "BACCARAT_DEAL_EXTRA_CARD"

    # Service errors
    STREAM_DOWN = "STREAM_DOWN"
    IDP_DOWN = "IDP_DOWN"
    SDP_DOWN = "SDP_DOWN"
    ZCAM_DOWN = "ZCAM_DOWN"
    BROKER_DOWN = "BROKER_DOWN"
    ROULETTE_DOWN = "ROULETTE_DOWN"
    SHAKER_DOWN = "SHAKER_DOWN"
    BARCODE_SCANNER_DOWN = "BARCODE_SCANNER_DOWN"
    PC_DOWN = "PC_DOWN"

    # Game flow errors
    NO_START = "NO_START"
    NO_BETSTOP = "NO_BETSTOP"
    NO_DEAL = "NO_DEAL"
    NO_FINISH = "NO_FINISH"
    JSON_PARSE_ERR = "JSON_PARSE_ERR"


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

            # Create connection URL according to CIT spec:
            # wss://studio-api.iki-cit.cc/v1/ws?id={device_id}&token=0000
            # For CIT, the id format is: device_id (e.g., ARO-002-2, ARO-001-1, ASB-001-1)
            connection_url = f"{self.server_url}?id={self.device_name}&token={self.token}"

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
    table_id: str = None,
    device_id: str = None,
    signal_type: str = "warn",
) -> bool:
    """
    Send roulette sensor stuck error signal for Roulette table.

    Args:
        table_id: Table ID for the Roulette game (default: None, will use device_id to determine)
        device_id: Device ID for the connection (default: None, will use config or default)
        signal_type: Signal type, 'warn' for first time, 'error' for second time (default: 'warn')

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

        SERVER_URL = config.get("server_url", "wss://studio-api.iki-cit.cc/v1/ws")
        TOKEN = config.get("token", "0000")

        # Log received parameters FIRST - this ensures we can see what was passed
        logger.info(f"📋 Received parameters: table_id={table_id}, device_id={device_id}")

        # CRITICAL: If device_id is provided, use it directly - DO NOT override
        # Only resolve from config if device_id is None
        if device_id is None:
            logger.info("   - device_id not provided, trying to resolve from config...")
            # Try to get device_id from device_mapping or use default from tables
            if "device_mapping" in config and table_id:
                # Look up device_id from table_id
                for dev_id, mapping in config["device_mapping"].items():
                    if mapping.get("table_id") == table_id:
                        device_id = dev_id
                        logger.info(f"   - Found device_id from mapping: {device_id}")
                        break
            
            # If still None, try to get from tables config
            if device_id is None:
                for table in config.get("tables", []):
                    if table.get("table_id") == table_id or table.get("name") == table_id:
                        device_id = table.get("device_id")
                        if device_id:
                            logger.info(f"   - Found device_id from tables: {device_id}")
                            break
            
            # Default fallback
            if device_id is None:
                device_id = "ARO-001-1"  # Default device
                logger.warning(f"   - Using default device_id: {device_id}")
        else:
            # IMPORTANT: device_id was provided - use it directly
            logger.info(f"   - Using provided device_id: {device_id} (DO NOT OVERRIDE)")

        # Determine table_id from device_id if not provided
        if table_id is None:
            logger.info("   - table_id not provided, extracting from device_id...")
            # Extract table_id from device_id (e.g., ARO-001-1 -> ARO-001)
            if '-' in device_id:
                parts = device_id.split('-')
                if len(parts) >= 3:
                    # For ARO-001-1, take ARO-001
                    table_id = f"{parts[0]}-{parts[1]}"
                elif len(parts) == 2:
                    table_id = device_id
                else:
                    table_id = device_id
            else:
                table_id = device_id
            logger.info(f"   - Extracted table_id: {table_id}")
        else:
            logger.info(f"   - Using provided table_id: {table_id}")

        # Log final resolved values BEFORE using them
        logger.info(f"📋 Final resolved values:")
        logger.info(f"   - Server: {SERVER_URL}")
        logger.info(f"   - Device: {device_id}")
        logger.info(f"   - Table: {table_id}")

    except FileNotFoundError:
        logger.error(f"❌ Configuration file not found: {config_path}")
        # Use CIT environment defaults
        SERVER_URL = "wss://studio-api.iki-cit.cc/v1/ws"
        TOKEN = "0000"
        if device_id is None:
            device_id = "ARO-001-1"
        if table_id is None:
            table_id = "ARO-001"
        logger.warning(f"Using default CIT configuration: {SERVER_URL}")
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in configuration file: {e}")
        return False
    except KeyError as e:
        logger.error(f"❌ Missing required configuration key: {e}")
        return False

    # Create error signal client
    # Use device_id as the connection identifier (for CIT environment format)
    client = ErrorSignalClient(SERVER_URL, table_id, device_id, TOKEN)

    try:
        # Connect to the table
        logger.info(f"🔗 Connecting to {table_id}...")
        if not await client.connect():
            logger.error(f"❌ Failed to connect to {table_id}")
            return False

        logger.info(f"✅ Successfully connected to {table_id}")

        # Create roulette sensor stuck error signal according to spec
        # signalType: 'warn' for first time, 'error' for second time
        signal_data = {
            "msgId": ErrorMsgId.ROULETTE_SENSOR_STUCK.value,
            "content": "Sensor broken causes roulette machine idle",
            "metadata": {
                "title": "SENSOR STUCK",
                "description": "Sensor broken causes roulette machine idle",
                "code": "ARE.3",
                "suggestion": "Clean or replace the ball",
                "signalType": signal_type,  # 'warn' or 'error'
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


async def send_roulette_wrong_ball_dir_error(
    table_id: str = None,
    device_id: str = None,
    signal_type: str = "warn",
) -> bool:
    """
    Send roulette wrong ball direction error signal for Roulette table.

    Args:
        table_id: Table ID for the Roulette game (default: None, will use device_id to determine)
        device_id: Device ID for the connection (default: None, will use config or default)
        signal_type: Signal type, 'warn' for first time, 'error' for second time (default: 'warn')

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

        SERVER_URL = config.get("server_url", "wss://studio-api.iki-cit.cc/v1/ws")
        TOKEN = config.get("token", "0000")

        # Log received parameters FIRST - this ensures we can see what was passed
        logger.info(f"📋 Received parameters: table_id={table_id}, device_id={device_id}")

        # If device_id is provided, use it directly; otherwise try to resolve from config
        if device_id is None:
            logger.info("   - device_id not provided, trying to resolve from config...")
            # Try to get device_id from device_mapping or use default from tables
            if "device_mapping" in config and table_id:
                # Look up device_id from table_id
                for dev_id, mapping in config["device_mapping"].items():
                    if mapping.get("table_id") == table_id:
                        device_id = dev_id
                        logger.info(f"   - Found device_id from mapping: {device_id}")
                        break
            
            # If still None, try to get from tables config
            if device_id is None:
                for table in config.get("tables", []):
                    if table.get("table_id") == table_id or table.get("name") == table_id:
                        device_id = table.get("device_id")
                        if device_id:
                            logger.info(f"   - Found device_id from tables: {device_id}")
                            break
            
            # Default fallback
            if device_id is None:
                device_id = "ARO-001-1"  # Default device
                logger.warning(f"   - Using default device_id: {device_id}")
        else:
            logger.info(f"   - Using provided device_id: {device_id} (DO NOT OVERRIDE)")

        # Determine table_id from device_id if not provided
        if table_id is None:
            logger.info("   - table_id not provided, extracting from device_id...")
            # Extract table_id from device_id (e.g., ARO-001-1 -> ARO-001)
            if '-' in device_id:
                parts = device_id.split('-')
                if len(parts) >= 3:
                    # For ARO-001-1, take ARO-001
                    table_id = f"{parts[0]}-{parts[1]}"
                elif len(parts) == 2:
                    table_id = device_id
                else:
                    table_id = device_id
            else:
                table_id = device_id
            logger.info(f"   - Extracted table_id: {table_id}")
        else:
            logger.info(f"   - Using provided table_id: {table_id}")

        # Log final resolved values BEFORE using them
        logger.info(f"📋 Final resolved values:")
        logger.info(f"   - Server: {SERVER_URL}")
        logger.info(f"   - Device: {device_id}")
        logger.info(f"   - Table: {table_id}")

    except FileNotFoundError:
        logger.error(f"❌ Configuration file not found: {config_path}")
        # Use CIT environment defaults
        SERVER_URL = "wss://studio-api.iki-cit.cc/v1/ws"
        TOKEN = "0000"
        if device_id is None:
            device_id = "ARO-001-1"
        if table_id is None:
            table_id = "ARO-001"
        logger.warning(f"Using default CIT configuration: {SERVER_URL}")
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in configuration file: {e}")
        return False
    except KeyError as e:
        logger.error(f"❌ Missing required configuration key: {e}")
        return False

    # Create error signal client
    # Use device_id as the connection identifier (for CIT environment format)
    client = ErrorSignalClient(SERVER_URL, table_id, device_id, TOKEN)

    try:
        # Connect to the table
        logger.info(f"🔗 Connecting to {table_id}...")
        if not await client.connect():
            logger.error(f"❌ Failed to connect to {table_id}")
            return False

        logger.info(f"✅ Successfully connected to {table_id}")

        # Create roulette wrong ball direction error signal according to spec
        # signalType: 'warn' for first time, 'error' for second time
        signal_data = {
            "msgId": ErrorMsgId.ROUELTTE_WRONG_BALL_DIR.value,
            "content": "ball is recognized spinning toward the wrong direction in the rim",
            "metadata": {
                "title": "WRONG BALL DIRECTION",
                "description": "ball is recognized spinning toward the wrong direction in the rim",
                "code": "ARE.4",
                "suggestion": "Check the sensor, it usually is due to sensor mis-recognize the direction",
                "signalType": signal_type,  # 'warn' or 'error'
            },
        }

        # Send the error signal
        logger.info(
            f"📤 Sending roulette wrong ball direction error signal to {table_id}..."
        )
        logger.info(f"   - Signal: {signal_data}")

        success = await client.send_error_signal(signal_data)

        if success:
            logger.info(
                "🎯 Roulette wrong ball direction error signal sent successfully!"
            )
        else:
            logger.error(
                "❌ Failed to send roulette wrong ball direction error signal"
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
