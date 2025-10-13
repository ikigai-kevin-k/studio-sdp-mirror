#!/usr/bin/env python3
"""
Test script for updating SDP status to down for Roulette Game (ARO-001 table).
Based on ws_sr_update.py functionality.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any

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


async def update_sdp_down_status(
    table_id: str = "ARO-001",
    fast_mode: bool = True,
) -> bool:
    """
    Update SDP status to down for Roulette game.
    Once WebSocket connection is established, it will not disconnect unless an exception occurs.
    If a connection already exists for the same table, it will reuse it instead of reconnecting.

    Args:
        table_id: Table ID for the Roulette game (default: ARO-001)
        fast_mode: Enable fast connection mode to skip welcome message wait (default: True)

    Returns:
        bool: True if update successful, False otherwise
    """

    global _ws_client, _table_id

    # SDP down status for Roulette game
    sdp_down_status = {
        "sdp": "down",
    }

    # Check if we already have a connection to the same table
    if _ws_client is not None and _table_id == table_id:
        try:
            # Try to check if the existing connection is still valid
            logger.info(
                f"🔗 Reusing existing WebSocket connection to {table_id}"
            )

            # Send the SDP down status update using existing connection
            logger.info(f"📤 Sending SDP down status update to {table_id}...")
            logger.info(f"   - Status: {sdp_down_status}")

            await _ws_client.send_multiple_updates(sdp_down_status)

            # Wait a shorter moment for the update to be processed
            await asyncio.sleep(0.1)

            # Show update results
            logger.info("\n" + "=" * 50)
            logger.info(f"📊 SDP DOWN UPDATE RESULTS FOR {table_id}")
            logger.info("=" * 50)

            preferences = _ws_client.get_server_preferences()
            summary = _ws_client.get_sent_updates_summary()

            logger.info(
                f"✅ Accepted fields: {preferences['accepted_fields']}"
            )
            logger.info(
                f"❌ Rejected fields: {preferences['rejected_fields']}"
            )
            logger.info(f"📊 Total updates sent: {summary['total_updates']}")

            # Check if SDP field was accepted
            sdp_accepted = "sdp" in preferences["accepted_fields"]

            if sdp_accepted:
                logger.info(
                    "🎯 SDP down status update was accepted successfully!"
                )
            else:
                logger.warning("⚠️  SDP field was rejected by server")

            logger.info(
                f"🔗 WebSocket connection to {table_id} maintained for future use"
            )
            return True

        except Exception as e:
            logger.warning(
                f"⚠️  Existing connection failed, will create new connection: {e}"
            )
            # Reset the client if the existing connection failed
            _ws_client = None
            _table_id = None

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

    except FileNotFoundError:
        logger.error(f"❌ Configuration file not found: {config_path}")
        return False
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in configuration file: {e}")
        return False
    except KeyError as e:
        logger.error(f"❌ Missing required configuration key: {e}")
        return False

    # Create new client for specified table with fast mode option
    client = SmartStudioWebSocketClient(
        SERVER_URL, table_id, DEVICE_NAME, TOKEN, fast_connect=fast_mode
    )

    try:
        # Connect to the table
        logger.info(f"🔗 Connecting to {table_id}...")
        if not await client.connect():
            logger.error(f"❌ Failed to connect to {table_id}")
            return False

        logger.info(f"✅ Successfully connected to {table_id}")

        # Store the client instance globally for reuse
        _ws_client = client
        _table_id = table_id

        # Send the SDP down status update
        logger.info(f"📤 Sending SDP down status update to {table_id}...")
        logger.info(f"   - Status: {sdp_down_status}")

        await client.send_multiple_updates(sdp_down_status)

        # Wait a shorter moment for the update to be processed
        await asyncio.sleep(0.1)

        # Show update results
        logger.info("\n" + "=" * 50)
        logger.info(f"📊 SDP DOWN UPDATE RESULTS FOR {table_id}")
        logger.info("=" * 50)

        preferences = client.get_server_preferences()
        summary = client.get_sent_updates_summary()

        logger.info(f"✅ Accepted fields: {preferences['accepted_fields']}")
        logger.info(f"❌ Rejected fields: {preferences['rejected_fields']}")
        logger.info(f"📊 Total updates sent: {summary['total_updates']}")

        # Check if SDP field was accepted
        sdp_accepted = "sdp" in preferences["accepted_fields"]

        if sdp_accepted:
            logger.info("🎯 SDP down status update was accepted successfully!")
        else:
            logger.warning("⚠️  SDP field was rejected by server")

        # Note: Connection is maintained and not disconnected
        logger.info(
            f"🔗 WebSocket connection to {table_id} maintained for future use"
        )

        return True

    except Exception as e:
        logger.error(f"❌ Error during SDP down status update: {e}")
        # Only disconnect on exception
        try:
            await client.disconnect()
            logger.info(f"✅ Disconnected from {table_id} due to exception")
            # Reset global variables on exception
            _ws_client = None
            _table_id = None
        except Exception as disconnect_error:
            logger.error(
                f"❌ Error disconnecting from {table_id}: {disconnect_error}"
            )
        return False


async def main():
    """Main function for testing the SDP down status update functionality."""

    logger.info("🎰 Roulette Game SDP Down Status Update Test")
    logger.info("=" * 50)

    # Test: Update SDP status to down
    logger.info("\n📤 Test: Updating SDP status to down...")
    success = await update_sdp_down_status()

    if success:
        logger.info("✅ SDP down status update completed successfully")
    else:
        logger.error("❌ SDP down status update failed")

    logger.info("\n🎯 Test completed!")


if __name__ == "__main__":
    asyncio.run(main())
